const puppeteer = require('puppeteer');

(async () => {
  console.log('--- LAUNCHING BROWSER V2 ---');
  const browser = await puppeteer.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security'] 
  });
  const page = await browser.newPage();
  
  // Capture Console - Essential
  page.on('console', msg => {
      const type = msg.type();
      const text = msg.text();
      // Filter out boring React warnings if needed, but for now keep all
      console.log(`BROWSER [${type.toUpperCase()}]: ${text}`);
  });

  page.on('pageerror', err => {
      console.log(`PAGE ERROR: ${err.message}`);
  });

  console.log('--- NAVIGATING ---');
  try {
      await page.goto('http://54.166.148.159', { waitUntil: 'domcontentloaded', timeout: 30000 });
      console.log('--- PAGE LOADED ---');
  } catch (e) {
      console.error('NAV FAIL:', e.message);
      await browser.close();
      process.exit(1);
  }

  // Check if API_URL is correct in console
  const config = await page.evaluate(() => window.config);
  console.log('WINDOW.CONFIG:', JSON.stringify(config));

  console.log('--- UPLOADING FILE ---');
  const filePath = '/Users/deepanshuverma/Downloads/Dummy Legal docs/SampleContract-Shuttle.pdf';
  
  try {
      const input = await page.$('input[type="file"]');
      if (!input) throw new Error('Input not found');
      await input.uploadFile(filePath);
      console.log('--- UPLOAD INITIATED ---');

      // Wait for success alert dialog
      await new Promise((resolve, reject) => {
          page.once('dialog', async dialog => {
             console.log('DIALOG DETECTED:', dialog.message());
             await dialog.dismiss();
             resolve();
          });
          
          // Timeout
          setTimeout(() => reject(new Error('Timeout waiting for Dialog')), 15000);
      });
      
      console.log('### SUCCESS: UPLOAD DIALOG RECEIVED ###');

  } catch (e) {
      console.log('### FAILURE: ###', e.message);
      await page.screenshot({ path: 'local_upload_fail_v2.png' });
  }

  await browser.close();
})();
