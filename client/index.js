const { Client, LocalAuth, Poll, DefaultOptions, MessageTypes } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const client = new Client({
    authStrategy: new LocalAuth()
});

// Map to store poll messages by chat ID
const pollMessages = new Map();

client.on('qr', qr => {
    qrcode.generate(qr, {small: true});
});

client.on('ready', () => {
    console.log('Client is ready!');
});

client.on('message', async message => {
    console.log('Received message:', message.body);
    
});

client.initialize();
