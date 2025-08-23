#!/usr/bin/env python3
"""
EVE Online API Integration
Adapted for web application with caching and error handling
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TradeOpportunity:
    item_id: int
    item_name: str
    buy_price: float
    sell_price: float
    profit_per_unit: float
    profit_margin: float
    volume: float
    max_units_by_cargo: int
    max_units_by_orders: int
    total_profit_potential: float
    isk_investment: float

class EVETradeAPI:
    def __init__(self):
        self.base_url = "https://esi.evetech.net/latest"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EVE-Routes/1.0 (https://github.com/your-repo/eve-routes)',
            'Accept': 'application/json'
        })
        
        # Region IDs  
        self.regions = {
            'jita': 10000002,      # The Forge (Jita)
            'dodixie': 10000032,   # Sinq Laison (Dodixie)
            'amarr': 10000043,     # Domain (Amarr)
            'rens': 10000030,      # Heimatar (Rens)
            'hek': 10000042        # Metropolis (Hek)
        }

        # Station IDs
        self.stations = {
            'jita': 60003760,      # Jita IV - Moon 4 - Caldari Navy Assembly Plant
            'dodixie': 60011866,   # Dodixie IX - Moon 20 - Federation Navy Assembly Plant
            'amarr': 60008494,     # Amarr VIII (Oris) - Emperor Family Academy
            'rens': 60004588,      # Rens VI - Moon 8 - Brutor Tribe Treasury
            'hek': 60005686       # Hek VIII - Moon 12 - Boundless Creation Factory
        }
        
        self.type_names = {}  # Cache for item names
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
    def _rate_limited_request(self, url: str, params: dict = None, timeout: int = 30) -> Optional[requests.Response]:
        """Make a rate-limited request to EVE API"""
        # Ensure we don't exceed rate limits
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            self.last_request_time = time.time()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {url} - {e}")
            return None
        
    def get_item_name(self, type_id: int) -> str:
        """Get item name by type_id with caching"""
        if type_id not in self.type_names:
            try:
                url = f"{self.base_url}/universe/types/{type_id}/"
                response = self._rate_limited_request(url)
                
                if response and response.status_code == 200:
                    data = response.json()
                    self.type_names[type_id] = data.get('name', f'Unknown_{type_id}')
                else:
                    logger.warning(f"Failed to get name for type_id {type_id}")
                    self.type_names[type_id] = f'Unknown_{type_id}'
                    
            except Exception as e:
                logger.error(f"Error getting item name for {type_id}: {e}")
                self.type_names[type_id] = f'Error_{type_id}'
        
        return self.type_names[type_id]
    
    def get_market_orders(self, region_id: int, order_type: str = 'all') -> List[Dict]:
        """Get market orders for a region with improved error handling"""
        all_orders = []
        page = 1
        max_pages = 50  # Safety limit
        
        logger.info(f"Fetching {order_type} orders for region {region_id}")
        
        while page <= max_pages:
            try:
                url = f"{self.base_url}/markets/{region_id}/orders/"
                params = {
                    'order_type': order_type,
                    'page': page
                }
                
                response = self._rate_limited_request(url, params)
                
                if response is None:
                    logger.error(f"No response for page {page}")
                    break
                
                if response.status_code == 200:
                    orders = response.json()
                    if not orders:  # Empty page means we're done
                        break
                    all_orders.extend(orders)
                    page += 1
                    
                    if page % 10 == 0:
                        logger.info(f"Fetched {page-1} pages, {len(all_orders)} orders so far")
                        
                elif response.status_code == 404:
                    # No more pages
                    break
                else:
                    logger.error(f"Error fetching orders page {page}: {response.status_code}")
                    break
                    
            except Exception as e:
                logger.error(f"Exception fetching page {page}: {e}")
                break
                
        logger.info(f"Finished fetching orders: {len(all_orders)} total")
        return all_orders
    
    def filter_station_orders(self, orders: List[Dict], station_id: int) -> List[Dict]:
        """Filter orders by station"""
        return [order for order in orders if order['location_id'] == station_id]
    
    def get_types_info_batch(self, type_ids: List[int]) -> Dict[int, Dict]:
        """Get type information with better error handling"""
        types_info = {}
        
        logger.info(f"Fetching info for {len(type_ids)} item types")
        
        for i, type_id in enumerate(type_ids):
            try:
                url = f"{self.base_url}/universe/types/{type_id}/"
                response = self._rate_limited_request(url)
                
                if response and response.status_code == 200:
                    data = response.json()
                    types_info[type_id] = {
                        'name': data.get('name', f'Unknown_{type_id}'),
                        'volume': data.get('volume', 0)
                    }
                else:
                    logger.warning(f"Failed to get info for type_id {type_id}")
                    
                # Progress logging
                if (i + 1) % 50 == 0:
                    logger.info(f"Fetched info for {i + 1}/{len(type_ids)} items")
                    
            except Exception as e:
                logger.error(f"Error fetching info for type_id {type_id}: {e}")
                continue
                
        logger.info(f"Successfully fetched info for {len(types_info)} items")
        return types_info

    def find_trade_opportunities(self, from_station: str, to_station: str, 
                               max_cargo: float = 33500, min_profit: float = 100000) -> List[TradeOpportunity]:
        """Find trade opportunities between two stations"""
        
        logger.info(f"Starting trade analysis: {from_station.upper()} → {to_station.upper()}")
        logger.info(f"Parameters: cargo={max_cargo:,.0f}m³, min_profit={min_profit:,.0f} ISK")
        
        # Get region and station IDs
        from_region = self.regions[from_station.lower()]
        to_region = self.regions[to_station.lower()]
        from_station_id = self.stations[from_station.lower()]
        to_station_id = self.stations[to_station.lower()]
        
        # Get market orders
        from_orders = self.get_market_orders(from_region, 'sell')
        to_orders = self.get_market_orders(to_region, 'buy')
        
        logger.info(f"Retrieved {len(from_orders)} sell orders and {len(to_orders)} buy orders")
        
        # Filter by stations
        from_station_orders = self.filter_station_orders(from_orders, from_station_id)
        to_station_orders = self.filter_station_orders(to_orders, to_station_id)
        
        logger.info(f"Filtered to {len(from_station_orders)} sell orders and {len(to_station_orders)} buy orders at stations")
        
        # Create price lookup dictionaries
        sell_orders = {}  # type_id -> list of orders
        buy_orders = {}   # type_id -> list of orders
        
        for order in from_station_orders:
            type_id = order['type_id']
            if type_id not in sell_orders:
                sell_orders[type_id] = []
            sell_orders[type_id].append(order)
            
        for order in to_station_orders:
            type_id = order['type_id']
            if type_id not in buy_orders:
                buy_orders[type_id] = []
            buy_orders[type_id].append(order)
        
        # Find potentially profitable items
        common_items = list(set(sell_orders.keys()) & set(buy_orders.keys()))
        logger.info(f"Found {len(common_items)} common items between stations")
        
        # Pre-filter profitable items
        potentially_profitable = []
        
        for type_id in common_items:
            try:
                # Get best prices
                best_sell = min(sell_orders[type_id], key=lambda x: x['price'])
                best_buy = max(buy_orders[type_id], key=lambda x: x['price'])
                
                buy_price = best_sell['price']
                sell_price = best_buy['price']
                
                if sell_price > buy_price:
                    profit_per_unit = sell_price - buy_price
                    # Only keep items with decent profit per unit
                    if profit_per_unit >= 10000:  # 10k ISK minimum
                        potentially_profitable.append({
                            'type_id': type_id,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'profit_per_unit': profit_per_unit,
                            'best_sell_volume': best_sell['volume_remain'],
                            'best_buy_volume': best_buy['volume_remain']
                        })
            except Exception as e:
                logger.error(f"Error processing type_id {type_id}: {e}")
                continue
        
        logger.info(f"Found {len(potentially_profitable)} potentially profitable items")
        
        # Get detailed type information
        type_ids = [item['type_id'] for item in potentially_profitable]
        types_info = self.get_types_info_batch(type_ids)
        
        # Calculate final opportunities
        opportunities = []
        
        for item in potentially_profitable:
            type_id = item['type_id']
            
            if type_id not in types_info:
                continue
                
            type_info = types_info[type_id]
            volume = type_info.get('volume', 0)
            
            if volume <= 0:
                continue
            
            # Calculate opportunity metrics
            profit_per_unit = item['profit_per_unit']
            profit_margin = (profit_per_unit / item['buy_price']) * 100
            
            # Calculate maximum units
            max_units_by_cargo = int(max_cargo / volume)
            max_units_by_orders = min(item['best_sell_volume'], item['best_buy_volume'])
            max_units = min(max_units_by_cargo, max_units_by_orders)
            
            if max_units <= 0:
                continue
                
            total_profit = profit_per_unit * max_units
            isk_investment = item['buy_price'] * max_units
            
            if total_profit >= min_profit:
                item_name = type_info.get('name', f'Unknown_{type_id}')
                
                opportunity = TradeOpportunity(
                    item_id=type_id,
                    item_name=item_name,
                    buy_price=item['buy_price'],
                    sell_price=item['sell_price'],
                    profit_per_unit=profit_per_unit,
                    profit_margin=profit_margin,
                    volume=volume,
                    max_units_by_cargo=max_units_by_cargo,
                    max_units_by_orders=max_units_by_orders,
                    total_profit_potential=total_profit,
                    isk_investment=isk_investment
                )
                
                opportunities.append(opportunity)
        
        # Sort by total profit potential
        opportunities.sort(key=lambda x: x.total_profit_potential, reverse=True)
        
        logger.info(f"Analysis complete: {len(opportunities)} profitable opportunities found")
        
        return opportunities