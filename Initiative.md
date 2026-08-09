Basically I want to build a Car Valuator platform focusing on Alberta market in Canada.

- Currently focus on pickup firstly, Will extend to sedan and SUV/MPV later on
- Use the most advanced and free web crawl framework/technologies to web crawl down some dataset from autorader.ca and cargurus.ca websites (may extended to other website as needed)
- I have prepared a simple Car Valuator Excel file: ford-ranger-201902023.xlsx and it's related valuation method in a markdown file, even plus a Python code in the subfolder: Ford-Ranger as an example.
- The web crawl framework can be anything, for instance: Firecrawl, Playwright, Crawl4AI, Scrapy, while the first 2 are preferred, since they are not based on one single language, but multiple, say Node.js.
- Please advise a best-fit Valuation model out of the market, I was using Python's statsmodels to conduct a simple regression using 2 parameters ("Year" and "Mileage") to predict Y ("Price") in my example, please feel free to advise a better one since the parameters can be quite a few, 3 to 5 per se?
- Database wise: a simple file based SQLite3 file shall be enough to handle the case.
- The app shall have sleek frontend UI and admin panel based backend, where the admin can perform or schedule the web crawling, as such to update the source dataset for prediction. A visitor log shall be in place to use my service.

Please prepare the PRD.md and related AGENTS.md.