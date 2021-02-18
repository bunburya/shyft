# Shyft - a self-hosted fitness tracker

Shyft is (or will be, once it is finished) a self-hosted solution for displaying and analysing activity data from popular
fitness tracking accessories and apps. It is open source software intended to be run on your local machine rather than
accessed over the internet, and can be viewed in your web browser. Because the data and software will all be stored 
locally, Shyft's fundamental functionality will not rely on any third party service and so will not be vulnerable
to, for example, a service provider's servers going down, or a service provider discontinuing functionality or moving to
a paid model. Some optional features may rely on (free) third party services - for example, the map display currently
relies on [OpenStreetMap](https://www.openstreetmap.org).

Shyft is written in Python and uses [Plotly/Dash](https://plotly.com/dash/) to display activity data. A full list of
the dependencies is available in the Pipfile.

Shyft is an early work in progress.