# Analyst Agent Frontend

A simple, clean frontend for testing the Analyst Agent API.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start the Frontend
```bash
npm run dev
```

The frontend will be available at: **http://localhost:3001**

### 3. Start the Analyst Agent API
In another terminal:
```bash
cd ..
python run.py
```

The API will be available at: **http://localhost:8000**

## ✨ Features

- **Clean, Modern UI** - Beautiful responsive design
- **Example Questions** - Click to try common queries
- **Multiple Dialects** - Support for all database types
- **Real-time Results** - See generated SQL and data
- **Error Handling** - Clear error messages
- **Mobile Friendly** - Works on all screen sizes

## 🧪 Testing

### Example Questions to Try:
- "Show me total sales by month for the last 6 months"
- "What are the top 5 products by revenue?"
- "How many active users do we have this week?"
- "What is the average order value by customer segment?"

### Database Options:
- **SQLite** - Best for local testing (no setup required)
- **PostgreSQL** - Production database
- **MySQL** - Popular choice
- **Snowflake** - Cloud data warehouse
- **BigQuery** - Google Cloud
- **SQL Server** - Microsoft
- **DuckDB** - Analytics database

## 🔧 Configuration

The frontend automatically connects to:
- **API**: `http://localhost:8000`
- **Frontend**: `http://localhost:3001`

To change the API URL, edit the `API_BASE` constant in `index.html`.

## 📁 Files

- `index.html` - Main frontend application
- `package.json` - Node.js dependencies  
- `README.md` - This file

## 🎨 Customization

The frontend is a single HTML file with embedded CSS and JavaScript for simplicity. You can easily customize:

- **Colors**: Edit the CSS gradient variables
- **Layout**: Modify the grid and flexbox layouts
- **Features**: Add new form fields or result displays
- **Styling**: Update the CSS for your brand

## 🚨 CORS Note

The frontend includes CORS headers for local development. For production, configure your API server to allow cross-origin requests from your frontend domain.

## 🤝 Usage

1. **Enter your question** in natural language
2. **Select your database dialect**
3. **Fill in connection details** (for testing, SQLite needs no setup)
4. **Click "Analyze Data"** to get results
5. **View the generated SQL** and data preview

Perfect for testing and demonstrating the Analyst Agent capabilities! 