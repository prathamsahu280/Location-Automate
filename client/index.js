const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const express = require('express');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth()
});

client.on('qr', qr => {
    qrcode.generate(qr, {small: true});
});

client.on('ready', () => {
    console.log('Client is ready!');
});

let messageCache = {};

client.on('message', async message => {
    console.log('Received message:', message.body);

    if(/^\d+$/.test(message.body) && message.body.length >= 10) {
        let phoneNumber = message.body;
        if (message.body.length > 10) {
            phoneNumber = phoneNumber.slice(-10);
        }
        const url = `https://digitalapiproxy.paytm.com/v1/mobile/getopcirclebyrange?channel=web&version=2&number=${phoneNumber}&child_site_id=1&site_id=1&locale=en-in`;

        try {
            const response = await axios.get(url);
            const data = response.data;
            if (data && data.Operator) {
                const operator = data.Operator;
                let author = message.from;
                author = author.trim("@c.us")
                let date = message.timestamp;
                date = new Date(date * 1000);
                date.setTime(date.getTime() + (5 * 60 + 30) * 60 * 1000);
                date = date.toUTCString();

                // Send data to Python server
                const result = await axios.post('http://localhost:5001/send', {
                    phone_number: phoneNumber,
                    operator: operator,
                    author: author,
                    date: date

                });

                if (result.data.status === 'success') {
                    await message.react("✅");
                    // Cache the message
                    messageCache[phoneNumber] = message;
                } else {
                    await message.reply('Error sending message.');
                }
            } else {
                await message.reply('Invalid number! Please enter a valid 10-digit number');
            }
        } catch (error) {
            console.error('Error fetching operator information:', error);
            await client.sendMessage(message.from, 'There was an error fetching the operator information. Please try again later.');
        }
    }
});

// Endpoint to receive replies from Python server
app.post('/reply', async (req, res) => {
    const { phone_number, reply } = req.body;
    const originalMessage = messageCache[phone_number];
    if (originalMessage) {
        await originalMessage.reply(reply);
        delete messageCache[phone_number]; // Remove from cache after replying
        res.status(200).send('Reply sent successfully');
    } else {
        res.status(404).send('Original message not found');
    }
});

app.listen(3000, () => {
    console.log('Node.js server is running on port 3000');
});

client.initialize();
