Other Details
==============

This page documents the various auxiliary commands and topics that are used in the application.


VAPID Keys
----------
VAPID (Voluntary Application Server Identity) Keys are used mainly to send and receive website push notifications.

To generate a VAPID keypair: :code:`npx web-push generate-vapid-keys`


JWKs
----
JWKs (Json Web keys) are used to perform open-id verification

To generate JWKs run :code:`python manage.py generate_jwks` in virtual environment,

the obtained base64 string needs to be exported to environment as :code:`JWKS_BASE64`
