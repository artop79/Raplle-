const express = require('express');
const cors = require('cors');
const axios = require('axios');
const app = express();
const port = 8000;

// Используем CORS для всех маршрутов
app.use(cors());
app.use(express.json());

// API ключ Heygen - копируем из .env файла
const HEYGEN_API_KEY = 'MDRjZWE4NzRiMTQ2NDE4MDhiMTRjNTM0NWQ3MGY5Y2EtMTczNjc3MzI0MA==';

// Базовый URL для Heygen API
const HEYGEN_API_URL = 'https://api.heygen.com';

// Настройки для запросов к Heygen API
const heygenAxios = axios.create({
  baseURL: HEYGEN_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'X-Api-Key': HEYGEN_API_KEY
  }
});

// Прокси-роут для API Heygen
app.all('/api/v1/heygen/:path(*)', async (req, res) => {
  try {
    // Получаем путь из параметра :path
    const path = req.params.path;
    console.log(`Proxy request to Heygen API: ${req.method} ${path}`);
    
    // Делаем запрос к Heygen API
    const response = await heygenAxios({
      method: req.method,
      url: path,
      data: req.method !== 'GET' ? req.body : undefined,
      params: req.method === 'GET' ? req.query : undefined
    });
    
    console.log(`Heygen API response status: ${response.status}`);
    return res.status(response.status).json(response.data);
  } catch (error) {
    console.error('Error proxying request to Heygen API:', error.message);
    
    // Отправляем ошибку клиенту
    if (error.response) {
      return res.status(error.response.status).json(error.response.data);
    } else {
      return res.status(500).json({ error: error.message });
    }
  }
});

// Маршрут для получения аватаров
app.get('/api/v1/avatars', async (req, res) => {
  try {
    console.log('Fetching avatars from Heygen API');
    const response = await heygenAxios.get('/v1/avatar.list');
    console.log(`Got ${response.data?.data?.length || 0} avatars`);
    return res.json({ avatars: response.data.data, status: 'success' });
  } catch (error) {
    console.error('Error fetching avatars:', error.message);
    return res.status(500).json({ error: error.message });
  }
});

// Маршрут для создания сессии стриминга
app.post('/api/v1/streaming.new', async (req, res) => {
  try {
    console.log('Creating new streaming session', req.body);
    const response = await heygenAxios.post('/v1/streaming.new', req.body);
    console.log('Session created:', response.data);
    return res.json(response.data);
  } catch (error) {
    console.error('Error creating streaming session:', error.message);
    return res.status(500).json({ error: error.message });
  }
});

// Базовый маршрут для проверки
app.get('/api/v1/status', (req, res) => {
  res.json({ status: 'ok', message: 'Proxy server is running' });
});

// Запуск сервера
app.listen(port, () => {
  console.log(`Proxy server is running on http://localhost:${port}`);
});
