# Quran Pages Scraper

A simple Python web-scraping project that retrieves Quran pages from [islamicbook.ws](https://www.islamicbook.ws/6/) and saves them locally.

This repository is primarily a **demo project** for:

* Simple web scraping with Python
* HTML parsing with BeautifulSoup
* HTTP requests and retry handling
* Basic automation with GitHub Actions
* CI/CD examples
* **Vibe coding** — using AI-assisted development to quickly build and experiment with a working project

> [!Note]
> This is a demonstration/learning project. Please respect the source website's terms of use, copyright, and server resources when running or modifying the scraper.

## Project Structure

```text
.
├── .github/
│   └── workflows/
│       └── quran.yml
├── Quran/
│   └── ...
├── allQuran.py
└── Quranenv.yml
```

### `allQuran.py`

The main Python script responsible for retrieving and saving the Quran pages.

The downloaded pages are stored in:

```python
output_directory = "Quran"
```

### `Quranenv.yml`

Conda environment definition containing the Python dependencies required by the scraper.

### `.github/workflows/quran.yml`

GitHub Actions workflow used to demonstrate CI/CD automation.

The workflow can automatically run the scraper and commit updated files to the repository.

## Data Source

The scraper retrieves data from:

```text
https://www.islamicbook.ws/6/
```

The URL follows a simple structure:

```text
https://www.islamicbook.ws/6/n.html
│       │                  │ │
│       │                  │ └── Page number
│       │                  └──── Directory / book identifier
│       └───────────────────── Website
└───────────────────────────── Protocol
```

### URL Components

#### `https://`

The protocol used to access the website securely over HTTPS.

#### `www.islamicbook.ws`

The website/domain hosting the source pages.

#### `/6/`

The directory used by the website for this particular collection.

In this project, `6` identifies the Quran collection being retrieved.

#### `n.html`

The individual page.

The `n` represents the page number.

For example:

```text
https://www.islamicbook.ws/6/1.html
https://www.islamicbook.ws/6/2.html
https://www.islamicbook.ws/6/3.html
...
```

The scraper can therefore construct URLs by changing the page number:

```python
url = f"https://www.islamicbook.ws/6/{page}.html"
```

Conceptually:

```text
https://www.islamicbook.ws/6/1.html
                         └─┬─┘
                           │
                         page 1

https://www.islamicbook.ws/6/2.html
                         └─┬─┘
                           │
                         page 2
```

The page count can be controlled by the scraper, allowing it to iterate through the expected page range.So the scraper retrieves the corresponding **PNG image** for each page.

For example, page 1 is available as:

```text
https://www.islamicbook.ws/6/1.png
```

The same URL pattern applies to the other pages:

```text
https://www.islamicbook.ws/6/1.png
https://www.islamicbook.ws/6/2.png
https://www.islamicbook.ws/6/3.png
...
```

The `.html` URL represents the web page, while the `.png` URL represents the corresponding page image.

The scraper downloads these PNG images and saves them locally in the `Quran/` output directory.

Conceptually:

```text
Pages
├── https://www.islamicbook.ws/6/1.png   → PNG image 1
├── https://www.islamicbook.ws/6/2.png   → PNG image 2 
├── https://www.islamicbook.ws/6/3.png   → PNG image 3 
└── https://www.islamicbook.ws/6/4.png   → PNG image 4
```


## CI/CD Demo

The GitHub Actions workflow demonstrates a basic automated pipeline:

```text
GitHub
   │
   ▼
GitHub Actions
   │
   ▼
Set up Python
   │
   ▼
Install dependencies
   │
   ▼
Run allQuran.py
   │
   ▼
Retrieve Quran pages
   │
   ▼
Save files to Quran/
   │
   ▼
Commit changes
   │
   ▼
Push updated files to GitHub
```

The workflow can be triggered:

* When changes are pushed to `main`
* On a scheduled basis
* Manually using `workflow_dispatch`

This is intentionally a simple CI/CD example rather than a production-grade scraping infrastructure.

## Technologies

* Python
* `requests`
* `BeautifulSoup`
* Git
* GitHub
* GitHub Actions
* Conda

## Disclaimer

This project is intended for **educational and demonstration purposes**.

The Quran pages are retrieved from the external website described above 

## License

The source code in this repository is licensed under the MIT License.
