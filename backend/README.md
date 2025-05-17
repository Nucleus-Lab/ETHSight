

""" will be called when the user first connect their wallet"""

# POST for create or GET a new user
# - check if the user exists in the database, if yes, return the user id, else, create a new user and return the user id
# - create a new user in the database
# - return a success response

""" will be called when the user first authenticated to display the latest canvas as the default canvas """

# POST get or create a new canvas
# - check if the canvas exists in the database, if yes, return the canvas id, else, create a new canvas and return the canvas id
# - create a new canvas in the database
# - return a success response


""" main endpoint for user interaction """

# POST for sending message 
# - check if the canvas exists using get_or_create_canvas, if yes, get the canvas, else, create a new canvas and get the canvas
# - create a new message and save it to the database
# - send the message to the AI agent
# - return a success response

""" for the file explorer in the frontend """

# GET for getting all canvases of a user (wallet address to user id to canvas id)
# - get the user id from the wallet address
# - get all the canvas that has user_id = current user id
# - return all the canvas id

""" for preview in file explorer in the frontend """

# GET the first message of a canvas by canvas id
# - get the first message of the canvas
# - return the message

# GET the first visualization of a canvas by canvas id
# - get the first visualization of the canvas
# - return the visualization






