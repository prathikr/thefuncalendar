# thefuncalendar

TODO:
- add local live score update feature
- figure out how to make this appeal to women
- potentially add tv show release schedules?
- MMA would get Karan on board 
- CFB/CBB (need to select a subset of all colleges to support)
- payment system, $0.99/month for premium
- compatible with apple calendar 👀 other calendar apps too?
- Hide spoilers feature where the score doesn’t update until 24hrs after the game incase you want to catch the replay (inspired by mlb.tv lol)
- change event creation to be 10 requests at a time and use exponential backoff for throttling, send user confirmation email and then notification when calendar is ready kinda like how gametime does when buying tickets. limit is 600 req/min so keep a pace of 300 req/min to start
- add tv network details 
- settings page to enable or disable elements on the dashboard for premium members
- TESTING FRAMEWORK
- set up dev website along with main site and local
- settings page for premium users to enable/disable any premium feature
- add an advertisement to free page
- ensure that updates to database don't overwrite existing users or their subscriptions
- move from heroku cli to github actions


Completed:
- local mvp with mlb teams working
- add nba functionality
- get livesite working
- Fix format of title, should be “SF vs LAD” when SF is home and “SF @ LAD” when away
- error with NFL functionality
- make calendar store formatting better
- NHL
- SOCCER!!! ⚽️ would prolly get Habbu and Nark on board as customerzzz
- IPL


Free Feature
- Manually subscribe to calendars for the current season


Premium Features
- Calendars auto-update after each season
- Automatically adds playoff schedule
- Live scores are uploaded to your google calendar
- Adds game details to description like probable starting pitchers, starting 5, injury report details, broadcast data
- No ads