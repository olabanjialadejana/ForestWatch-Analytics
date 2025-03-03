import ee

def authenticate_and_initialize():
    try:
        ee.Initialize()
        print('GEE initialized (existing token).')
    except:
        # if token is expired, try to refresh it
        # based on https://stackoverflow.com/questions/53472429/how-to-get-a-gcp-bearer-token-programmatically-with-python
        try:
            import google.auth
            import google.auth.transport.requests
            creds, project = google.auth.default()
            # creds.valid is False, and creds.token is None
            # refresh credentials to populate those
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            # initialise GEE session with refreshed credentials
            ee.Initialize(creds)
            print('GEE initialized (refreshed token).')
        except:
            # get the user to authenticate manually and initialize the session
            ee.Authenticate()
            ee.Initialize()
            print('GEE initialized (manual authentication).')