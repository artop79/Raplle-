const express = require('express');
const cors = require('cors');
const axios = require('axios');
const app = express();
const port = 8000;

// Используем CORS для всех маршрутов
app.use(cors());
app.use(express.json());

// API ключ Heygen
const HEYGEN_API_KEY = 'MDRjZWE4NzRiMTQ2NDE4MDhiMTRjNTM0NWQ3MGY5Y2EtMTczNjc3MzI0MA==';

// Базовый URL для Heygen API
const HEYGEN_API_URL = 'https://api.heygen.com';

// Создаем экземпляр axios для запросов к Heygen API
const heygenAxios = axios.create({
  baseURL: HEYGEN_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'X-Api-Key': HEYGEN_API_KEY
  }
});

// Маршрут для получения списка аватаров
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

// Маршрут для создания новой сессии стриминга
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

// Маршрут для запуска сессии стриминга
app.post('/api/v1/streaming.start', async (req, res) => {
  try {
    console.log('Starting streaming session', req.body);
    const response = await heygenAxios.post('/v1/streaming.start', req.body);
    console.log('Session started:', response.data);
    return res.json(response.data);
  } catch (error) {
    console.error('Error starting streaming session:', error.message);
    return res.status(500).json({ error: error.message });
  }
});

// Маршрут для отправки текста в сессию стриминга
app.post('/api/v1/streaming.task', async (req, res) => {
  try {
    console.log('Sending task to streaming session', req.body);
    const response = await heygenAxios.post('/v1/streaming.task', req.body);
    console.log('Task sent:', response.data);
    return res.json(response.data);
  } catch (error) {
    console.error('Error sending task to streaming session:', error.message);
    return res.status(500).json({ error: error.message });
  }
});

// Маршрут для остановки сессии стриминга
app.post('/api/v1/streaming.stop', async (req, res) => {
  try {
    console.log('Stopping streaming session', req.body);
    const response = await heygenAxios.post('/v1/streaming.stop', req.body);
    console.log('Session stopped:', response.data);
    return res.json(response.data);
  } catch (error) {
    console.error('Error stopping streaming session:', error.message);
    return res.status(500).json({ error: error.message });
  }
});

// Базовый маршрут для проверки работоспособности
app.get('/api/v1/status', (req, res) => {
  res.json({ status: 'ok', message: 'Proxy server is running' });
});

// Запуск сервера
app.listen(port, () => {
  console.log(`Proxy server is running on http://localhost:${port}`);
});
