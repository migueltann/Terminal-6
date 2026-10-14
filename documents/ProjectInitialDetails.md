# Project Initial Details

Team Name: Terminal 6

## Problem Statement and Target Users
Planning a trip is time-consuming because travellers must compare activities, restaurants, accommodation and shopping against their budget and requirements. Researching many sources takes effort, and it is easy to pick options that break a budget or a dietary need.

Terminal-6 is an AI-powered Travel Recommendation Assistant. It uses Google Gemini to discover destination-specific options in four categories: activities, food, accommodation and shopping. Python logic then checks every option against the user’s hard requirements and records why it passed or failed. The application runs in the terminal, has an optional Flask web interface, and runs in Docker.

It is intended for individual travellers, students, families and small groups who want personalised recommendations without researching and comparing options manually.

Objectives: generate personalised recommendations for a destination; keep results within the user’s budget for each category; respect environment, dietary, transport and avoid-list requirements; explain every pass or fail; and let users save, reopen, filter and delete recommendation sets.



## User Inputs
2. User Inputs
Users enter the following in the terminal, grouped by category:

- Destination: a city, country, country code or “City, Country”.
- Activities: preferred activities, maximum spend per activity (SGD), indoor/outdoor/any environment.
- Food: cuisine preferences, maximum spend per meal (SGD), environment, dietary requirement.
- Accommodation: accommodation preferences, maximum spend per night (SGD).
- Shopping: shopping preferences, maximum shopping spend (SGD), environment.
- Universal restrictions: preferred transport (walk, transit, taxi or any) and an avoid list.

Preferences can be left blank or entered as “Any” or “None”, which means no preference. Inputs are validated: destinations are checked against geonamescache with “Did you mean...?” suggestions, budgets must be positive numbers, and environment and transport must be one of the listed options. Invalid input is rejected and the user is asked again. Users can type back or exit, and can confirm, edit one input or restart from a summary screen.


## Use of AI
3. Use of AI
The AI is the core engine: every request passes through Gemini, and without it the application has nothing to filter. The system sends the destination and the four category preferences, and asks for exactly 60 candidates (15 per category). When preferences exist for a category, about 10 candidates relate to them and 5 are general, so users still discover popular options. The AI does not create an itinerary and does not filter or rank. Hard restrictions are applied only in Python.

Gemini returns a JSON array. Each item has its name, type, category, estimated cost in SGD, location, environment, description, tags, transport options and dietary tags (shopping items also have shopping types and interests).

Responses are validated before use. The AI Manager checks the response is valid JSON in the expected shape. If the output is malformed, or none of the items are usable, it retries and falls back across three Gemini models, and temporary errors (HTTP 429 and 5xx) are retried with increasing waits. The Logic Manager then checks each item’s fields, types, cost and environment and discards invalid items.


## Business Rules
4. Business Rules
The Logic Manager marks a recommendation eligible only if it passes every rule that applies, and records PASS or FAIL with a reason for each.

Category budget: cost must not exceed the budget for that category (activity, meal, accommodation per night, shopping).
Environment: for activities, food and shopping, the environment must match the user’s choice unless it is “Any”.
Avoid list: rejected if its name, category, description, location or tags match an avoided term.
Dietary requirement: food must list the user’s dietary requirement in its dietary tags.
Transport: the preferred transport must be among the item’s transport options unless it is “Any”.
Top pick (multi-condition rule): an eligible item is flagged as a top pick when it matches one of the user’s preferences for its category and costs no more than half of that category’s budget. If the user gave no preferences for a category, the three cheapest eligible items within half the budget are flagged instead.

Preferences guide discovery and the top-pick flag. They are not used as hard filters.

Final Output: approved recommendations are grouped into the four categories with name, category, location, environment, estimated cost, description, tags, transport options, passed rules and any top-pick reason. Filtered-out items are shown separately with their failed rules. Users can save results as JSON and CSV and view, filter by destination or delete saved sets. If the AI fails or returns nothing usable, an error is shown and the user returns to the main menu.

Code Repository URL: https://github.com/migueltann/Terminal-6.git (Dockerfile in the repository root)


## Code Repository URL
[https://github.com/migueltann/Terminal-6.git]