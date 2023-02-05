import logging
import time
from io import BytesIO
import sys
import traceback
from PIL import Image
from selenium.common.exceptions import WebDriverException

single_screens = []

logger: logging.Logger | None = None


def stitch_screenshot_parts():
    global logger, single_screens
    logger.debug('Start stitching')
    total_height = -1
    max_scroll = -1
    max_width = -1
    images = dict()
    parts = list()
    for img_tupel in single_screens:
        # Load image from disk and parse params out of filename
        img_obj = Image.open(BytesIO(img_tupel[0]))
        width, height = img_obj.size
        parts.append((img_tupel[0], width, height))
        curr_scroll = img_tupel[2]
        #curr_scroll = int(curr_scroll.split('.')[0])
        index = int(img_tupel[1])

        # Update output image size
        if curr_scroll > max_scroll:
            max_scroll = curr_scroll
            total_height = max_scroll + height

        if width > max_width:
            max_width = width

        # Save image parameters
        img = {}
        img['object'] = img_obj
        img['scroll'] = curr_scroll
        images[index] = img

    # Output filename same for all parts, so we can just use last filename
    logger.debug(f'{max_width} {total_height}')
    output = Image.new('RGB', (int(max_width), int(total_height)))
    temp = BytesIO()
    # Compute dimensions for output image
    for i in range(max(images.keys()) + 1):
        img = images[i]
        output.paste(im=img['object'], box=(0, int(img['scroll'])))
        img['object'].close()
    try:
        output.save(temp, format='jpeg')
        return temp
    except SystemError:
        logger.error("BROWSER: SystemError while trying to save screenshot .Slices of image Final size .")
        pass


def execute_script_with_retry(driver, script):
    try:
        return driver.execute_script(script)
    except WebDriverException:
        time.sleep(1)
        return driver.execute_script(script)


def screenshot_full_page(driver, lo, retry=False, loading_wait=0.0):
    global single_screens, logger
    logger = lo
    logger.debug('Start the process')
    single_screens = []
    try:
        part = 0
        max_height = execute_script_with_retry(
            driver, 'return document.body.scrollHeight;')
        inner_height = execute_script_with_retry(
            driver, 'return window.innerHeight;')
        curr_scrollY = execute_script_with_retry(
            driver, 'return window.scrollY;')
        prev_scrollY = -1
        single_screens.append((driver.get_screenshot_as_png(), part, curr_scrollY))
        while (curr_scrollY + inner_height) < max_height and \
                curr_scrollY != prev_scrollY:

            # Scroll down to bottom of previous viewport
            try:
                driver.execute_script('window.scrollBy(0, window.innerHeight)')
            except WebDriverException:
                logger.error("BROWSER: WebDriverException while scrolling, screenshot may be misaligned!")
                pass

            # Update control variables
            part += 1
            prev_scrollY = curr_scrollY
            curr_scrollY = execute_script_with_retry(
                driver, 'return window.scrollY;')

            # Save screenshot
            time.sleep(loading_wait)
            single_screens.append((driver.get_screenshot_as_png(), part, curr_scrollY))
    except WebDriverException:
        excp = traceback.format_exception(*sys.exc_info())
        logger.error(f'BROWSER: Exception while taking full page screenshot: \n {excp}')
        if not retry:
            return screenshot_full_page(driver, retry=True, lo=logger, loading_wait=loading_wait)
        return

    return stitch_screenshot_parts()
