const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

const client = new Client({
    authStrategy: new LocalAuth()
});

client.on('qr', qr => {
    qrcode.generate(qr, {small: true});
});

client.on('ready', () => {
    console.log('Client is ready!');
});

client.on('message', async message => {
    console.log('Received message:', message.body);

    // Check if the message contains a 10-digit number
    if(/^\d+$/.test(message.body) && message.body.length >= 10) {
        let phoneNumber = message.body;
        if(message.body.length>10){
            let exceededlength = message.body.length - 10 ;
            phoneNumber = phoneNumber.substring(exceededlength,message.body.length);
        }
        const url = `https://digitalapiproxy.paytm.com/v1/mobile/getopcirclebyrange?channel=web&version=2&number=${phoneNumber}&child_site_id=1&site_id=1&locale=en-in`;

        try {
            // Make a request to the API to get the operator information
            const response = await axios.get(url);
            const data = response.data;
            if (data && data.Operator) {
                let operator = data.Operator
            } else {
                await message.reply('Invalid number! Please enter a valid 10 digit number');
            }

            // React to the message
            await message.react("✅");
        } catch (error) {
            console.error('Error fetching operator information:', error);
            await client.sendMessage(message.from, 'There was an error fetching the operator information. Please try again later.');
        }
    }
});

client.initialize();
