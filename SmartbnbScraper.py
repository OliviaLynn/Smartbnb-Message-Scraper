from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import ays, time, json
from bs4 import BeautifulSoup

# SMARTBNB SCRAPER for python3
# Scrapes data from smartbnb.io and saves to .json  file
#
# Requires:
#   selenium, beautifulsoup4
# Must have the proper selenium chrome driver installed
#   Place that .exe in the same directory as the python script
#   and you're good to go
#
# Run this script in your IDE or via command line
#   $python /path/to/SmartbnbScraper <smartbnb-username> <smartbnb-password>

# Guessing a decent json format:
# { data: [
#           { url: ---,
#             msgs: [ { author: host,
#                       message: ---- },
#                     { author: guest,
#                       message: ---- },
#                     { author: guest,
#                       message: ---- }
#                   ] },
#           { url: ---,
#             msgs: [ { author: host,
#                       message: ---- },
#                     { author: host,
#                       message: ---- },
#                     { author: guest,
#                       message: ---- }
#                   ] }
#         ]
# }

# --- Small warning ---
#
# if (stack_overflow):
#     dont
#
# Hitting a stackoverflow error at page 507
# Time to diverge from selenium best practices!
#   Page 5, for example:
#   https://my.smartbnb.io/inbox/segments/default;offset=100;query=
#   The number after offset= is 20 * the page number
# Just added in a way to skip right to the page by modifying the url,
#   hope it works

VERBOSE = False

# How many pages we should scrape before saving
PAGES_PER_BATCH = 10

# Keep this a multiple of however many pages are in a save batch
# Also, note there's no zero-indexing technically, but you can make this 0 because it will
#   then start saving after 
START_SAVING_AFTER_PAGE = 0

def run():    
    # Initialization
    
    chrome_options = Options()
    # Runs the driver without opening a new chrome window
    #   (helps when running it in the bg, but makes it harder to debug)
    #chrome_options.add_argument("--headless")
    chrome_options.add_argument('log-level=1')
    browser = webdriver.Chrome(chrome_options=chrome_options)
    url = "https://my.smartbnb.io/"
    browser.get(url)

    # Login, navigate to inbox
    if len(sys.argv) != 3:
        print("Improper arguments given: should be <username> <password>")
        return
    else:
        username = sys.argv[1]
        password = sys.argv[2]
        doLogin(browser, username, password)
        openInbox(browser, START_SAVING_AFTER_PAGE)

    # Determine our last page
    totalPages = countPages(browser)
    print("TOTAL PAGES: {:d}".format(totalPages))
    
    # Initialize our data holder
    jsonData = { "data": [] }
    jsonData["totalPages"] = totalPages
    
    # Skip a page just to give a wide berth to current conversations
    nextPageAndMaybeSave(browser, jsonData, START_SAVING_AFTER_PAGE)
    # This will recursively crawl through pages

    print("\nFinished scraping!")

def saveJson(jsonData, page):
    fileName = 'TESTdata{:d}.json'.format(page)
    print("Saving to " + fileName + "...")
    
    # Save our current data
    with open(fileName, 'w') as outfile:
        json.dump(jsonData, outfile)
    print("Saved JSON as " + fileName)
    
    # Reset our data holder so we can add fresh data
    jsonData["data"] = []
        
def doLogin(browser, username, password):
    # Check that the page has loaded and the login fields are actually there (45 second timeout)
    WebDriverWait(browser, 45).until(EC.presence_of_element_located((By.CLASS_NAME, "mat-input-element")))

    # Locate the username and pw fields
    fields = browser.find_elements_by_class_name("mat-input-element")
    fields[0].send_keys(username)
    fields[1].send_keys(password)

    # Click the submit button
    submitButton = browser.find_element_by_class_name("login__btn-submit")
    submitButton.click()

def openInbox(browser, pageNumber):
    if VERBOSE:
        print("Opening inbox...")
    try:
        # Make sure we're able to load the post-login page before navigating away
        WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.CLASS_NAME, "clickable")))
        # Then navigatge to the inbox
        if pageNumber == 0:
            browser.get("https://my.smartbnb.io/inbox")
        elif pageNumber > 0:
            browser.get("https://my.smartbnb.io/inbox/segments/default;offset={:d};query=".format(20*pageNumber))
        print("Opened inbox at page {:d}.".format(pageNumber))
    except:
        print("Could not load inbox.")
        return

def examinePage(browser, jsonData, pageNumber):
    try:
        WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.CLASS_NAME, "mat-button-toggle-label-content")))
    except:
        print("Could not load inbox page.")
        return

    if pageNumber <= START_SAVING_AFTER_PAGE:
        nextPageAndMaybeSave(browser, jsonData, pageNumber)

    # Only grab from message threads that have already been read
    inboxItems = browser.find_elements_by_class_name("inbox__item-read")

    for i in range(len(inboxItems)):
        # Just in case the len of our inboxItems has changed while we were looking through the messages
        if (i >= len(inboxItems)):
            break
        
        # Grab the first message thread
        grabSingleMessageThread(browser, inboxItems[i], jsonData, pageNumber)

        # Go back to the inbox page
        # We could bypass this by, before ever leaving this page, grabbing the link to the next page, then the list of links to each message thread
        # This way would be counter to the style they suggest, but theoretically would save time
        browser.back()
        try:
            WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.CLASS_NAME, "inbox__item-read")))
        except:
            print("Could not load inbox page.")
            return
        inboxItems = browser.find_elements_by_class_name("inbox__item-read")
  
    nextPageAndMaybeSave(browser, jsonData, pageNumber)

def grabSingleMessageThread(browser, target, jsonData, pageNumber):
    link = target.get_attribute("href")
    
    if VERBOSE:
        print("------------------------------------------------------------------------------------------")
        print("TARGET: " + link)
        print("------------------------------------------------------------------------------------------")
    else:
        print(".", end = "")
        sys.stdout.flush()
        
    browser.get(link)
    msgs = getMessages(browser, pageNumber)
    newThread = {}
    newThread["url"] = link
    newThread["msgs"] = msgs
    jsonData["data"].append(newThread)

def getMessages(browser, pageNumber):
    try:
        WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.CLASS_NAME, "thread_message")))
    except:
        print("\nERROR: Could not load message thread page.")
        return [ {"error": "Could not load a thread on page {:d} of inbox".format(pageNumber)} ] 

    # Initialize our data storage list
    msgs = []

    # Find where the messages we're scraping are
    messageContainers = browser.find_elements_by_class_name("thread__message-container")

    # Go through the messages
    if VERBOSE:
        print("Printing messages...")
    for messageContainer in messageContainers:
        newMessage = { "author": "---", "message": "" }

        # Get the author of the message
        soup = BeautifulSoup(messageContainer.get_attribute('innerHTML'), 'html.parser')
        host = soup.find("div", {"class": "thread_message-host"})
        guest = soup.find("div", {"class": "thread_message-guest"})
        if (host):
            if VERBOSE:
                print("--> HOST", end = ": ")
            newMessage["author"] = "host"
        elif (guest):
            if VERBOSE:
                print("-> GUEST", end = ": ")
            newMessage["author"] = "guest"

        # Get the content of the message
        messageDiv = soup.find("div", {"class": "thread_message-auto-inner"})
        if messageDiv is not None:
            if VERBOSE:
                print(messageDiv.get_text()[:60].replace("\n", " ") + "...")
            newMessage["message"] = messageDiv.get_text()
        else:
            if VERBOSE:
                print("[ NoneType! ]")

        # Store the author/content into our msgs list
        msgs.append(newMessage)

    if VERBOSE:
        print("Messages printed.")
    return msgs

def nextPageAndMaybeSave(browser, jsonData, pageNumber):
    print()

    # Every x pages, we want to save the json, just in case
    if pageNumber % PAGES_PER_BATCH == 0 and pageNumber > START_SAVING_AFTER_PAGE:
        saveJson(jsonData, pageNumber)

    # Stop if we're on the last page
    if pageNumber >= jsonData["totalPages"]:    
        saveJson(jsonData, pageNumber)
        print("Last page reached!")
        return
    
    #print("Finding next page...")
    print("Going to page {:d}...".format(pageNumber+1))
    # Finds the > button and clicks it
    try:
        WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.CLASS_NAME, "paginator__prevnext")))
    except:
        print("Could not load paginators.")
        saveJson(jsonData, pageNumber)
        return
    
    paginators = browser.find_elements_by_class_name("paginator__prevnext")
    if (paginators[1].get_attribute("value") == "forward"):
        paginators[1].click()
        examinePage(browser, jsonData, pageNumber+1)
            
def countPages(browser):
    # Reads the pagination button and finds the last numerical label
    # This lets us know how many pages we want to scrape
    print("Counting pages...")
    try:
        WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.CLASS_NAME, "mat-button-toggle-label-content")))
    except:
        print("Could not load paginators.")
        return
    buttonLabels = browser.find_elements_by_class_name("mat-button-toggle-label-content")
    lastPageLabel = buttonLabels[len(buttonLabels)-2] # exclude the last label, which is the > button
    lastPageNumber = int(lastPageLabel.get_attribute('innerHTML'))
    return lastPageNumber





# ----------------------------------------------------------------


def goThroughPages(browser):
    print("Looking at pages...")

    # Find how many inbox pages there are
    try:
        WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.CLASS_NAME, "inbox__item")))
    except:
        print("Problem encountered with the loaded inbox.")
        return
    
    #numPages = countPages(browser)
    #print(str(numPages) + " PAGES")

    nextPage(browser)

    # Initialize our data holder
    examinePage(browser) # this will recursively call itself

def perusePages(browser, data, print_flag):
    try:
        # If we can't find a "checkin__container" element after 45 seconds of loading, fail
        WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.CLASS_NAME, "checkin__container")))
    except:
        print("Cannot load page.")
        return
    
    # Find how many Check-ins pages there are
    numPages = countPages(browser)
    print(str(numPages) + " PAGES")
    
    # Iterate through Check-ins pages
    print("ITERATING THROUGH PAGES")
    isCheckin = True
    prev0thRow = None
    for page in range(numPages):
        data, prev0thRow = singlePage(browser, data, isCheckin, page, prev0thRow, print_flag)
    
    # Switch to Check-outs tab
    switchTabs(browser)
    
    # Find how many Check-outs pages there are
    numPages = countPages(browser)
    print(str(numPages) + " PAGES")

    # Iterate through Check-outs pages
    print("ITERATING THROUGH PAGES")
    isCheckin = False
    for page in range(numPages):
        data, prev0thRow = singlePage(browser, data, isCheckin, page, prev0thRow, print_flag)
    
    return data

def singlePage(browser, data, isCheckin, page, prev0thRow, print_flag):
    if (print_flag):
        print("\nPAGE " + str(page+1)) # Add 1 to output because 0-indexing

    # Grab our row elements
    rows = browser.find_elements_by_class_name("checkin__container")

    # Wait until the rows we've grabbed are actually new rows
    while (prev0thRow != None and prev0thRow == rows[0]):
        rows = browser.find_elements_by_class_name("checkin__container")

    # Record our current 0th row for future reference
    prev0thRow = rows[0]
    
    # Extract our data from our rows
    for row in rows:
        row_data = getDataFromRow(row.get_attribute('innerHTML'), isCheckin, print_flag)
        if (len(row_data) > 0):
            data.append(row_data)
        
    # Navigate to the next page
    nextPage(browser)
        
    return data, prev0thRow

def switchTabs(browser):
    tab = browser.find_element_by_id("mat-tab-label-0-1")
    tab.click()
    print("Switched tab")
    
def getDataFromRow(row, isCheckin, print_flag):
    # Our final storage container
    row_data = {}
    
    # Parse html via the lovely Python package Beautiful Soup 4
    soup = BeautifulSoup(row, 'html.parser')

    # The names are stored in <strong> tags, and are the only <strong> tags on the page
    nametag = soup.find('strong')
    row_data["Name"] = nametag.get_text()

    # We find the rest of the data in <span> tags
    # If anything in thie program breaks, it will probably be this
    # This section is very dependent on how they structure their html, and won't
    #   work if they shift things around
    # Call print(soup.prettify()) to see the structure of the row html, which
    #   should help with rewriting this section if needed in the future
    spans = soup.find_all('span')
    row_data["Room ID"] = spans[0].get_text()
    row_data["Listing ID"] = spans[1].get_text()
    row_data["RawDates"] = spans[3].get_text()

    # Extrapolate from current data
    date_obj = datetime.strptime(row_data["RawDates"], "%b %d %Y - %H:%M")
    if notToday(date_obj):
        return {}
    row_data["Time"] = date_obj.strftime("%H:%M")
    row_data["Checkin"] = isCheckin
    row_data["Checkout"] = not isCheckin
    if (isCheckin):
        row_data["Late Checkout"] = False
        if (int(date_obj.hour) < 15):
            row_data["Early Checkin"] = True
        else:
            row_data["Early Checkin"] = False
    else:
        row_data["Early Checkin"] = False
        if (int(date_obj.hour) > 11):
            row_data["Late Checkout"] = True
        else:
            row_data["Late Checkout"] = False
    

    # Display each row we grab
    if (print_flag):
        print("{:20} | {:20} | {:12} | {}".format(row_data["Name"], row_data["Room ID"],
                                                  row_data["Listing ID"], row_data["Time"]))

    # Return json
    return row_data
        
def notToday(date_obj):
    return date_obj.date() != datetime.today().date()

def saveJsonOLD(data, json_path):
    with open(json_path, 'w') as json_file:
        json.dump(data, json_file)
    print("Wrote json.")

def saveCsv(data, csv_path):
    if (len(data) > 0):
        with open(csv_path, 'w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',')
            csv_writer.writerow(data[0].keys())
            for row in data:
                csv_writer.writerow(row.values())
    print("Wrote csv.")
    

if __name__ == "__main__":
    run()

