# Smartbnb Message Scraper
<img src="https://img.shields.io/badge/python-3.7-blue" /> <img src="https://img.shields.io/badge/selenium-1.141.0-blue" /> <img src="https://img.shields.io/badge/maintained%3F-no-red" /> <img src="https://img.shields.io/github/issues/OliviaLynn/Smartbnb-Message-Scraper" /> 

 Scrapes all message data from Smartbnb using Selenium.

## Getting Started

These instructions will get the project up and running on your own machine with your own Smartbnb account.

### Prerequisites

#### Selenium (1.141.0)
Our webscraper. Instructions assume you use Chrome, but you can substitute your preferred (selenium-supported) browser instead.
- Install selenium via pip
```shell
pip install selenium
```
- Check what version of Chrome you're using (Chrome menu in the top right > Help > About Google Chrome)
- The Selenium Chromedriver for your version of Chrome can be downloaded [here](https://chromedriver.chromium.org/downloads) (the one in this git is for version 78). Place this exe in the same directory as SmartbnbScraper.py

#### Beautiful Soup (4.7.1)
For parsing the html we scrape.
```shell
pip install beautifulsoup4
```

### Running
- In `SmartbnbScraper.py`, consider making changes to `PAGES_PER_BATCH` and `START_SAVING_AFTER_PAGE` as desired.
- From your shell, run the command:
```shell
$ python SmartbnbScraper.py <smartbnb-username> <smartbnb-password>
```

## Output
- Outputs json of format (where `url` points each specific the message thread):
```yaml
{ data: [
          { url: ---,
            msgs: [ { author: host,
                      message: ---- },
                    { author: guest,
                      message: ---- },
                    { author: guest,
                      message: ---- }
                  ] },
          { url: ---,
            msgs: [ { author: host,
                      message: ---- },
                    { author: host,
                      message: ---- },
                    { author: guest,
                      message: ---- }
                  ] }
        ]
}
```
- Several JSON files will be created, batching together however many inbox pages have been specified in `PAGES_PER_BATCH`. Each file name will be suffixed with the last (1-indexed) page included in its batch.
