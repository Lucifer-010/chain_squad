Arbiscan - L3 Orbit Chain Monitoring & Alerting Dashboard UI

This repository contains the front-end implementation for Arbiscan, a dedicated monitoring and alerting dashboard for Arbitrum L3 Orbit chains. It provides developers and operators with a powerful, at-a-glance interface to ensure their L3 chain is healthy, performant, and reliable.

The goal of this project is to move developers from a state of "hoping it works" to "knowing it works" by providing a single, easy-to-use tool for critical infrastructure monitoring.


✨ Key Features
This UI is built with a focus on functionality, clarity, and user experience.


Key Features:
This UI is built with a focus on functionality, clarity, and user experience.

Core UI & UX
-Fully Responsive Design: A fluid layout ensures a seamless experience on desktop, tablet, and mobile devices, allowing for monitoring on the go.

-Dual-Theme Interface (Dark/Light): A professionally designed dark and light mode toggle allows users to choose their preferred viewing experience, with the preference saved locally.

-Multi-language Support (i18n): The interface is built with internationalization in mind, supporting English, Spanish, Japanese, Korean, and French to accommodate global teams.

-Intuitive Mobile Navigation: A smooth, animated slide-out menu provides full access to all features on smaller screens.


Core Monitoring Components


The dashboard is designed to display the vital health metrics required for any production-grade L3 chain. The UI components are wired to display:


The dashboard is designed to display the vital health metrics required for any production-grade L3 chain. The UI components are wired to display:

-Key Health Metric Cards: Prominent cards at the top of the dashboard provide immediate insight into:
   1. Chain Uptime and current block number.
   2. Sequencer ETH Balance to monitor gas funds.
   3. Timestamp of the Last Batch posted to the parent L2.

-Real-time Data Tables: Clean and readable tables are designed to display:
   1. The latest transactions occurring on the L3.
   2. Key on-chain assets and their metrics.

-Interactive Data Charts: The UI includes three interactive charts built with Recharts to visualize historical data and trends for:
   1. Daily transaction volume (TPS).
   2. Unique active addresses over time.
   3. DeFi protocol volumes and TVL.

-Built-in Alerting Framework
The UI is designed to integrate with a backend alerting system. This allows it to serve as the front-end for a system that can trigger alerts via Telegram or Discord based on pre-defined critical thresholds, such as:

    1. ETH balance dropping below a set amount.
    2. No new blocks being produced for a specified time period (e.g., 5 minutes).


 Technology Stack

 Technology Stack:

This is a modern, lightweight front-end built with a focus on performance and maintainability.

     1. HTML5: Semantic and accessible markup.
     2. Tailwind CSS: A utility-first CSS framework for rapid and consistent styling.
     3. JavaScript (Vanilla): Powers all client-side interactivity, theme management, and data rendering.
     4. React & Recharts: Utilized via CDN to render beautiful and interactive data visualization charts without a complex build setup.


 Running the UI

 Running the UI:

 This project is self-contained within a single index.html file, requiring no installation or build steps.

     1.  the code as index.html.
     2. Open the index.html file in any modern web browser.


 Code Structure:



The entire application is encapsulated within the index.html file for ultimate portability and simplicity.

    1. <head>: This section loads all external dependencies (Tailwind, fonts, and charting libraries) from reliable CDNs. It also contains the initial scripts for theme and language management to ensure the correct state is loaded instantly without any page flicker.
    
    2. <body>: Contains the semantic HTML structure for all UI components, including the header, main dashboard grid, cards, tables, and chart containers.
    
    3. <script> (at the end of <body>): This block contains the application's core logic. It defines the mock data, includes functions to render this data into the HTML, and initializes the Recharts components to draw the charts. All event listeners for interactivity are also managed here.