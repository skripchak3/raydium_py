import puppeteer from 'puppeteer-core';
import fs from 'fs';
import { exec } from 'child_process';
import { isNumber } from 'puppeteer-core';

const PHOTON_URL = 'https://photon-sol.tinyastro.io';
const MIN_BUYERS_AMOUNT_USD = 320000;

async function connectBrowser() {
    const browser = await puppeteer.launch({
        headless: false,
        executablePath: '/usr/bin/google-chrome',
        userDataDir: './profiles',
        ignoreDefaultArgs: [
            '--enable-automation',
            '--disable-extensions'
        ],
        defaultViewport: null,
	timeout: 0,
        args: [
            '--enable-unsafe-swiftshader',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--display=:99',
            '--disable-web-security',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--enable-features=NetworkService,NetworkServiceInProcess',
            '--disable-extensions-except',
            '--load-extension',
            '--start-maximized',
            '--allow-chrome-as-default-browser',
            '--allow-file-access-from-files',
            '--enable-extensions',
            '--extensions-on-chrome-urls',
            '--allow-external-extensions',
            '--enable-extensions-file-access-check',
            '--enable-component-extensions-with-background-pages',
            '--disable-extensions-except=./extensions/phantom',
            '--load-extension=extensions/phantom',
            '--enable-sync'
        ],
    });
    return browser;
}

(async () => {
    const browser = await connectBrowser();
    const page = await browser.newPage();
    page.on('console', async (msg) => {
        try {
            console.log('puppeteer:', await Promise.all(msg.args().map(arg => arg.jsonValue())))
        } catch { }
    });

    let i = 0;

    try {
        await page.goto(PHOTON_URL, { waitUntil: 'networkidle2', timeout: 60000 });
        await page.exposeFunction('handleNewElement', async (coin) => {
            const coinInfo = await startAnalyzeCoinByTime(browser, coin);
            if (coinInfo) {
                console.log(coinInfo);
                exec(`echo 123qazzaq | sudo -S docker run -d --env-file .env --name bot${i} raydium --pair ${coinInfo.pair_address}`, (error, stdout, stderr) => {
                    console.log(error);
                    console.log(stderr);
                })
            }
        })
        await page.evaluate(() => {
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'childList') {
                        if (mutation.addedNodes.length > 0) {
                            mutation.addedNodes.forEach(node => {
                                const link = node.getAttribute('href');
                                let volume = node.querySelectorAll('a > div')[6].textContent;
                                volume = volume.includes('K') ? parseFloat(volume.slice(1, -1)) * 1000 : parseFloat(volume.slice(1));
                                let buyers = node.querySelector('span.c-indx-table__cell--green').textContent;
                                let sellers = node.querySelector('span.c-indx-table__cell--red').textContent;
                                buyers = parseFloat(buyers);
                                sellers = parseFloat(sellers);
                                const balance = parseFloat(document.querySelector('.c-header__item__title .js-generated-balance').textContent);
                                if (link) {
                                    const coin = {
                                        link,
                                        volume,
                                        txns: {
                                            buyers,
                                            sellers
                                        },
                                        balance
                                    }
                                    window.handleNewElement(coin);
                                }
                            });
                        }
                    }
                }
            });

            observer.observe(document.querySelector('div[data-table-id="discover"]'), {
                childList: true,
                subtree: true,
                characterData: true
            });
        });
    } catch (err) {
        console.error(err);
    }

})()

async function startAnalyzeCoinByTime(browser, coin) {
    try {
        const page = await browser.newPage();
        page.on('console', async (msg) => {
            try {
                console.log('puppeteer:', await Promise.all(msg.args().map(arg => arg.jsonValue())))
            } catch { }
        });

        await page.goto(PHOTON_URL + coin.link, { waitUntil: 'networkidle0', timeout: 60000 });
        await page.waitForSelector('span.p-show__pair__cur', { timeout: 600000 });
        const firstDep = await checkFirstDeps(page);
        const coinInfo = await page.evaluate(() => {
            const addresses = document.querySelectorAll('.p-show__bar__row > div > a');
            const token_address = addresses[0].getAttribute('href').replace('https://solscan.io/account/'); 
            const pair_address = addresses[1].getAttribute('href').replace('https://solscan.io/account/'); 
            // return `${pair_address},${token_address}`;
            return {pair_address}
        });
        await page.close();
        if (!firstDep) return false;
        return coinInfo;
    } catch (err) { console.error(err) }
}

async function checkFirstDeps(page) {
    await page.waitForSelector('.c-trades-table-wrapper .c-trades-table__tr--buy');
    return await page.evaluate((MIN_BUYERS_AMOUNT_USD) => {
        const currentYear = new Date().getFullYear();
        const currentTime = new Date();
        let totalUsd = 0;
        const allBuys = document.querySelectorAll('.c-trades-table-wrapper .c-trades-table__tr--buy');
        for (const buy of allBuys) {
            const buyTime = buy.querySelector('.c-grid-table__td span').textContent;
            const buyUsd = buy.querySelectorAll('.c-grid-table__td')[3].textContent.slice(1);
            const usd = buyUsd.endsWith("K") ? parseFloat(buyUsd.slice(0, -1))*1000 : parseFloat(buyUsd);
            const time = new Date(`${buyTime} ${currentYear}`);
            totalUsd += usd;
            if (Math.floor((currentTime - time))/1000 > 100) {
                return false;
            }
        }
        if (totalUsd < MIN_BUYERS_AMOUNT_USD) return false;
        return totalUsd;
    }, MIN_BUYERS_AMOUNT_USD);
}