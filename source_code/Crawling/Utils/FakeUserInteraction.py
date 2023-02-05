import time
from random import randint
from pyotp import random
from selenium.common import MoveTargetOutOfBoundsException, JavascriptException
from selenium.webdriver import ActionChains


def fake_user_interaction(selenium_driver):
        x = randint(0, 3)
        if x == 0:
            move_mouse_random(selenium_driver)
            return
        if x == 1:
            scroll_down(selenium_driver)
            return
        if x == 2:
            scroll_down(selenium_driver)
            move_mouse_random(selenium_driver)
            return
        if x == 3:
            move_mouse_random(selenium_driver)
            scroll_down(selenium_driver)


def move_mouse_random(driver):
    # bot mitigation 1: move the randomly around a number of times
    NUM_MOUSE_MOVES = 10
    window_size = driver.get_window_size()
    num_moves = 0
    num_fails = 0
    while num_moves < NUM_MOUSE_MOVES + 1 and num_fails < NUM_MOUSE_MOVES:
        try:
            if num_moves == 0:  # move to the center of the screen
                x = int(round(window_size['height'] / 2))
                y = int(round(window_size['width'] / 2))
            else:  # move a random amount in some direction
                move_max = randint(0, 500)
                x = randint(-move_max, move_max)
                y = randint(-move_max, move_max)
            action = ActionChains(driver)
            action.move_by_offset(x, y)
            action.perform()
            num_moves += 1
        except MoveTargetOutOfBoundsException:
            num_fails += 1
            pass


def scroll_down(driver):  # TODO: siehe youtube
    at_bottom = False
    try:
        while random() > .20 and not at_bottom:
            driver.execute_script("window.scrollBy(0,%d)" % (10 + int(200 * random())))
            at_bottom = driver.execute_script(
                "return (((window.scrollY + window.innerHeight ) + 100 ""> document.body.clientHeight ))")
            time.sleep(0.5 + random())
    except(JavascriptException):
        pass