import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './style.css';

const tg = (window as any).Telegram?.WebApp;
tg?.ready?.();
tg?.expand?.();
tg?.setHeaderColor?.('#0e5138');
tg?.setBackgroundColor?.('#f3f7f2');

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
