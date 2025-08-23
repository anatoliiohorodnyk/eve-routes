#!/usr/bin/env python3
"""
EVE Routes - Flask Web Application
Main application file
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import json
from eve_api import EVETradeAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['REDIS_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.config['RATE_LIMIT_PER_MINUTE'] = int(os.getenv('RATE_LIMIT_PER_MINUTE', '10'))
app.config['CACHE_TTL_SECONDS'] = int(os.getenv('CACHE_TTL_SECONDS', '300'))

# Initialize Redis
try:
    redis_client = redis.from_url(app.config['REDIS_URL'])
    redis_client.ping()
    logger.info("Connected to Redis successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Running without cache.")
    redis_client = None

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[f"{app.config['RATE_LIMIT_PER_MINUTE']} per minute"]
)

# Initialize EVE API
eve_api = EVETradeAPI()

def get_cache_key(from_station: str, to_station: str, max_cargo: int, min_profit: int) -> str:
    """Generate cache key for request parameters"""
    return f"opportunities:{from_station}:{to_station}:{max_cargo}:{min_profit}"

def get_cached_data(cache_key: str):
    """Get cached data from Redis"""
    if not redis_client:
        return None
    
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        logger.error(f"Cache read error: {e}")
    
    return None

def set_cached_data(cache_key: str, data, ttl_seconds: int):
    """Set cached data in Redis"""
    if not redis_client:
        return
    
    try:
        redis_client.setex(
            cache_key,
            ttl_seconds,
            json.dumps(data, default=str)
        )
    except Exception as e:
        logger.error(f"Cache write error: {e}")

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'redis': 'connected' if redis_client else 'disconnected',
            'eve_api': 'available'
        }
    }
    
    # Test Redis connection
    if redis_client:
        try:
            redis_client.ping()
            health_status['services']['redis'] = 'connected'
        except:
            health_status['services']['redis'] = 'error'
    
    return jsonify(health_status)

@app.route('/api/opportunities')
@limiter.limit(f"{app.config['RATE_LIMIT_PER_MINUTE']} per minute")
def get_opportunities():
    """API endpoint to get trade opportunities"""
    try:
        # Get parameters
        from_station = request.args.get('from_station', '').lower()
        to_station = request.args.get('to_station', '').lower()
        max_cargo = int(request.args.get('max_cargo', 33500))
        min_profit = int(request.args.get('min_profit', 100000))
        
        # Validate parameters
        valid_stations = ['jita', 'dodixie']
        if from_station not in valid_stations or to_station not in valid_stations:
            return jsonify({
                'error': 'Invalid station. Use jita or dodixie'
            }), 400
        
        if from_station == to_station:
            return jsonify({
                'error': 'From and to stations cannot be the same'
            }), 400
        
        if max_cargo <= 0 or max_cargo > 1000000:
            return jsonify({
                'error': 'Invalid cargo capacity. Must be between 1 and 1,000,000 m³'
            }), 400
        
        if min_profit < 0:
            return jsonify({
                'error': 'Minimum profit cannot be negative'
            }), 400
        
        # Check cache first
        cache_key = get_cache_key(from_station, to_station, max_cargo, min_profit)
        cached_result = get_cached_data(cache_key)
        
        if cached_result:
            logger.info(f"Returning cached result for {from_station}→{to_station}")
            return jsonify({
                'opportunities': cached_result['opportunities'],
                'metadata': {
                    **cached_result['metadata'],
                    'cached': True,
                    'cache_key': cache_key
                }
            })
        
        # Get fresh data
        start_time = datetime.utcnow()
        logger.info(f"Fetching opportunities: {from_station}→{to_station}, cargo={max_cargo}, profit={min_profit}")
        
        opportunities = eve_api.find_trade_opportunities(
            from_station=from_station,
            to_station=to_station,
            max_cargo=max_cargo,
            min_profit=min_profit
        )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Convert opportunities to dict format
        opportunities_data = []
        for opp in opportunities[:35]:  # Limit to top 35
            max_units = min(opp.max_units_by_cargo, opp.max_units_by_orders)
            opportunities_data.append({
                'item_id': opp.item_id,
                'item_name': opp.item_name,
                'buy_price': opp.buy_price,
                'sell_price': opp.sell_price,
                'profit_per_unit': opp.profit_per_unit,
                'profit_margin': opp.profit_margin,
                'volume': opp.volume,
                'max_units': max_units,
                'total_weight': max_units * opp.volume,
                'total_profit': opp.total_profit_potential,
                'investment': opp.isk_investment
            })
        
        # Prepare response
        result = {
            'opportunities': opportunities_data,
            'metadata': {
                'from_station': from_station,
                'to_station': to_station,
                'max_cargo': max_cargo,
                'min_profit': min_profit,
                'total_found': len(opportunities),
                'showing': len(opportunities_data),
                'query_time_seconds': round(duration, 2),
                'timestamp': end_time.isoformat(),
                'cached': False
            }
        }
        
        # Cache the result
        set_cached_data(cache_key, result, app.config['CACHE_TTL_SECONDS'])
        
        logger.info(f"Found {len(opportunities)} opportunities in {duration:.2f}s")
        return jsonify(result)
        
    except ValueError as e:
        logger.error(f"Parameter validation error: {e}")
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    
    except Exception as e:
        logger.error(f"Error getting opportunities: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal server error. Please try again later.'
        }), 500

@app.route('/api/cache/stats')
def cache_stats():
    """Get cache statistics"""
    if not redis_client:
        return jsonify({'error': 'Redis not available'}), 503
    
    try:
        info = redis_client.info()
        keys = redis_client.keys('opportunities:*')
        
        return jsonify({
            'redis_info': {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            },
            'cache_keys': len(keys),
            'cache_entries': [key.decode() for key in keys[:10]]  # Show first 10
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/clear')
def clear_cache():
    """Clear all cache entries"""
    if not redis_client:
        return jsonify({'error': 'Redis not available'}), 503
    
    try:
        keys = redis_client.keys('opportunities:*')
        if keys:
            redis_client.delete(*keys)
        
        return jsonify({
            'message': f'Cleared {len(keys)} cache entries',
            'cleared_keys': len(keys)
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'error': str(e)}), 500

# Static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'error': 'Rate limit exceeded. Please try again later.',
        'retry_after': str(e.retry_after)
    }), 429

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Run the app
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug_mode
    )