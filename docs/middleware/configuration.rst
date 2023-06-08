Connecting with Middleware
==========================

The requests from middleware server should contain:

 - The auth token must be of :code:`Middleware_Bearer` realm.
 - The configured :code:`facility_id` in :code:`X-Facility-Id` header.
 - The authentication header must contain :code:`asset_id` in the JWT.
