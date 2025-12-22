const puppeteer = require('puppeteer');

(async () => {
  console.log('--- LAUNCHING BROWSER ---');
  const browser = await puppeteer.launch({ headless: true }); // Headless for speed, set false to see it
  const page = await browser.newPage();

  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  
  console.log('--- NAVIGATING ---');
  await page.goto('http://54.166.148.159', { waitUntil: 'networkidle0' });

  console.log('--- UPLOADING FILE ---');
  const filePath = '/Users/deepanshuverma/Downloads/Dummy Legal docs/SampleContract-Shuttle.pdf';
  const input = await page.$('input[type="file"]');
  await input.uploadFile(filePath);

  console.log('--- WAITING FOR RESULT ---');
  try {
      // Wait for the "Success" alert or the document to appear in the list
      // Since alert() blocks puppeteer, we handle dialog
      page.on('dialog', async dialog => {
          console.log('DIALOG:', dialog.message());
          await dialog.dismiss();
      });

      // Also wait for the file name to appear in the table
      await page.waitForFunction(
          text => document.body.innerText.includes(text),
          { timeout: 10000 },
          'SampleContract-Shuttle.pdf'
      );
      console.log('SUCCESS: Document found in list!');
  } catch (e) {
      console.log('ERROR or TIMEOUT:', e.message);
      // Capture Screenshot on failure
      await page.screenshot({ path: 'local_upload_fail.png' });
  }

  await browser.close();
})();
