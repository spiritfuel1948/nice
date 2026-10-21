// Render the print-interior HTML to a 5.5 x 8.5 inch PDF with page numbers.
// Usage: node print_pdf.js <print.html> <out.pdf>   (needs Playwright)
const { chromium } = require('playwright');

(async () => {
  const [, , htmlPath, outPath] = process.argv;
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + htmlPath, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: outPath,
    width: '5.5in',
    height: '8.5in',
    preferCSSPageSize: true,
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate:
      '<div style="width:100%;text-align:center;font-family:serif;font-size:8pt;color:#333;">' +
      '<span class="pageNumber"></span></div>',
  });
  await browser.close();
})();
