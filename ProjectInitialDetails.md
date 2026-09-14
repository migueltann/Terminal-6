# Project Initial Details

Team Name: Terminal 6

## Problem Statement and Target Users
1. Problem Statement and Target Users
Planning a trip can be time-consuming because travellers need to consider attractions, activities, restaurants, cost, available time and travelling distance. It can be difficult to create an itinerary that fits within a fixed budget while matching the traveller's interests and preferences.
The Travel Itinerary Assistant aims to solve this problem by using AI to generate personalised travel options and create a practical day-to-day itinerary. The system considers the user's budget, available time, interests, dietary requirements and travel preferences when selecting and arranging options. It also aims to reduce unnecessary travelling by grouping activities located near each other.
The application is intended for individual travellers, students, families and small groups who want to create a personalised itinerary without manually comparing and arranging different travel options.
Objectives: Generate personalised recommendations, keep the itinerary within budget, fit activities within available time, consider dietary requirements, reduce unnecessary travelling and produce a practical day-to-day itinerary.


## User Inputs
2. User Inputs
Users will provide the following information through the terminal:
Trip details: Destination, trip start and end dates, number of travellers, travel budget, accommodation area, preferred start and end times.
Travel preferences: Interests, preferred activities, must-visit spots, locations or activities to avoid, travelling pace, maximum acceptable travel time, and preferred transportation method.
Personal requirements: Dietary requirements, accessibility requirements, age group (whether children or elderly travellers are included), and required rest periods.
The application will validate the user's inputs before processing them. Invalid inputs will be rejected and the user will be asked to enter them again.


## Use of AI
3. Use of AI
AI will be the main engine of the application, and every travel request will pass through the AI processing stage. The AI will use the user's destination, interests, activities and personal requirements to generate suitable attractions, activities and restaurants.
The AI will return a structured JSON response containing information such as the recommendation name and category, reason, estimated cost and duration, location, suggested time, transport method, travelling time, dietary suitability and accessibility suitability.
The AI will provide possible options rather than the final itinerary. The Logic Manager will filter and rank these options according to the user's requirements and business rules. AI responses will be validated to ensure that required fields are present and have the correct data types before they are used.


## Business Rules
4. Business Rules
The Logic Manager will filter and rank AI-generated recommendations based on the user's requirements.
Budget and Time
Recommendations will be rejected when:
The estimated cost exceeds the remaining budget;
The activity does not fit within the available time;
The activity overlaps with another scheduled activity; or
A lower-cost suitable option is available.
The number of activities selected will also consider the user's preferred travelling pace, with fewer activities selected for a relaxed pace.
Location and Travel
The system will prioritise activities located near each other to reduce unnecessary travelling. Recommendations will be rejected when the estimated travelling time exceeds the user's maximum acceptable travel time. The user's preferred transport method will also be considered when arranging the itinerary.
Suitability
Restaurants will only be selected when they meet the user's dietary requirements. Activities that do not meet accessibility requirements or are unsuitable for the travellers' age group will be rejected. This will also consider whether children or elderly travellers are included.
Recommendation Ranking
Suitable recommendations will be ranked based on factors such as matching the user's interests and preferred activities, fitting within the budget, meeting the maximum travelling time and being located near other selected activities.
A multi-condition rule will increase a recommendation's priority when the recommendation matches the user's interests, fits within the remaining budget and is within the user's maximum acceptable travelling time.
The highest-ranked suitable recommendations will then be arranged into the final day-by-day itinerary.
Final Output
The final output will contain selected activities, meal locations, estimated activity and travelling durations, estimated daily and total costs, recommended transport methods and reasons for the selected recommendations.
If the user's requirements cannot all be satisfied, the system will identify the conflicting requirements and inform the user that the budget, schedule or preferences need to be adjusted.


## Code Repository URL
[https://github.com/migueltann/Terminal-6.git]