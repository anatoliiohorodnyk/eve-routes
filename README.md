# 🚀 EVE Routes

**Find the most profitable trade routes in EVE Online**

A modern web application that helps EVE Online players discover profitable hauling opportunities between Jita and Dodixie trade hubs.

## ✨ Features

- 🎯 **Real-time Market Data** - Uses EVE ESI API for up-to-date prices
- 📦 **Custom Cargo Capacity** - Set your ship's cargo hold size
- 💰 **Profit Filtering** - Set minimum profit thresholds
- 🔄 **Bi-directional Routes** - Jita→Dodixie and Dodixie→Jita
- ⚡ **Fast & Cached** - Redis caching for better performance
- 🌐 **Web Interface** - Clean, responsive UI
- 🐳 **Docker Ready** - Easy deployment with Docker Compose

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Internet connection (for EVE ESI API)

### Running with Docker

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/eve-routes.git
   cd eve-routes
   ```

2. **Start the application**
   ```bash
   docker-compose up -d
   ```

3. **Access the web interface**
   - Main app: http://localhost:5000
   - Redis admin (debug): http://localhost:8081

### Development Mode

1. **Start with debug profile**
   ```bash
   docker-compose --profile debug up
   ```

2. **View logs**
   ```bash
   docker-compose logs -f web
   ```

## 🛠️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `RATE_LIMIT_PER_MINUTE` | `10` | API rate limit per IP |
| `CACHE_TTL_SECONDS` | `300` | Cache TTL (5 minutes) |

### Docker Compose Override

Create `docker-compose.override.yml` for custom settings:

```yaml
version: '3.8'
services:
  web:
    environment:
      - FLASK_ENV=development
    ports:
      - "3000:5000"  # Different port
```

## 📊 Usage

1. **Select Trade Route**
   - Choose between Jita→Dodixie or Dodixie→Jita

2. **Set Parameters**
   - Cargo capacity (m³)
   - Minimum profit threshold (ISK)

3. **View Results**
   - Sorted by total profit potential
   - Shows buy/sell prices, margins, and cargo requirements

## 🔧 API Endpoints

### GET `/api/opportunities`

Get trade opportunities

**Parameters:**
- `from_station` - Source station (jita/dodixie)
- `to_station` - Destination station (jita/dodixie) 
- `max_cargo` - Maximum cargo capacity in m³
- `min_profit` - Minimum profit threshold in ISK

**Example:**
```bash
curl "http://localhost:5000/api/opportunities?from_station=jita&to_station=dodixie&max_cargo=33500&min_profit=100000"
```

### GET `/health`

Health check endpoint

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│   Flask App     │◄──►│   EVE ESI API   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Redis Cache   │
                       └─────────────────┘
```

## 🚧 Development

### Local Development

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally**
   ```bash
   python app.py
   ```

### Project Structure

```
eve-routes/
├── app.py                 # Main Flask application
├── eve_api.py            # EVE ESI API integration
├── static/               # Frontend assets
│   ├── index.html
│   ├── style.css
│   └── script.js
├── templates/            # Jinja2 templates
├── logs/                 # Application logs
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is not affiliated with CCP Games or EVE Online. Use at your own risk. Always verify market data in-game before making trades.

## 🔗 Links

- [EVE Online](https://www.eveonline.com/)
- [EVE ESI API Documentation](https://esi.evetech.net/ui/)
- [EVE University Trading Guide](https://wiki.eveuniversity.org/Trading)

---

**Fly safe, trade smart!** o7