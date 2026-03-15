# SideQuest

A Flask website to suggest road trip detours based on user preferences.

## UI/UX Overview

### User-flow

0. Register/login for the ability to save preferences and routes (OPTIONAL)
1. Import or create road trip route
2. Set preferences for detours (type, maximum time, etc.)
3. View route on map, select detours to update route
4. Export new route to external application (Google Maps, Apple Maps, GPX, etc.)

### Interface

Single-page application (SPA), with OpenStreetMaps (OSM) as the primary element to interact with routes.
Additional options and information will be shown via modals/popups on top of the OSM map.

#### Map Interaction

- Route node markers and line, once a detour is added the original route is displayed as a dotted line
- Suggested detours (only markers) are marked in grey until added
- To toggle the view of a detour, click on the marker (see Detour Info element below)
- When a detour is being viewed, display the new route in grey (if it were to be added)
- Once added, detour marker displays as different color from original route markers

#### Elements/Modals

*Login/Register*
- username/password
- implement forgot password? would require user email

*Import Route*
- import from Google Maps, Apple Maps, or GPX file
- create route - input beginning, intermediary stops, and end
- select previously created route (if logged in)

*Export Route*
- export to Google Maps, Apple Maps, or GPX file (does this differ between desktop and mobile?)
- save to account (if logged in)

*Preferences*
- distance unit (metric, imperial)
- max (individual) detour time
- list of detour types and whether enabled or not (amusement parks, restaraunts, etc.)
- ability to select travel type? (car, bike, train, etc.)

*Route Info*
- original route distance & time
- updated route distance & time & # detours

*Detour Info*
- toggled view by clicking on detour marker on map
- add/remove/reject detour to route (reject removes suggestion completely)
- destination name, type, detour distance/time
- description
- link to more info?

