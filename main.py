"""### Importing the Libraries"""
import openai
import gradio
import os
from neo4j import GraphDatabase
from os import environ as env


"""### Initializing the Neo4j Client"""
neo4j_session = GraphDatabase.driver(uri=os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_AUTH_USER"), os.getenv("NEO4J_AUTH_PASSWORD")))
# db = neo4j_session.session()


"""### Initializing the OpenAI Api key"""
# openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")


"""### Examples for generating Cypher Queries (7-shot learning prompt)"""
examples = """
# I have already watched Top Gun
MATCH (u:User {id: $userId}), (m:Movie {title:"Top Gun"})
MERGE (u)-[:WATCHED]->(m)
RETURN distinct {answer: 'noted'} AS result
# I like Top Gun
MATCH (u:User {id: $userId}), (m:Movie {title:"Top Gun"})
MERGE (u)-[:LIKE_MOVIE]->(m)
RETURN distinct {answer: 'noted'} AS result
# What is a good comedy?
MATCH (u:User {id:$userId}), (m:Movie)-[:IN_GENRE]->(:Genre {name:"Comedy"})
WHERE NOT EXISTS {(u)-[:WATCHED]->(m)}
RETURN {movie: m.title} AS result
ORDER BY m.imdbRating DESC LIMIT 1
# Who played in Top Gun?
MATCH (m:Movie)<-[:ACTED_IN]-(a)
RETURN {actor: a.name} AS result
# What is the plot of the Copycat movie?
MATCH (m:Movie {title: "Copycat"})
RETURN {plot: m.plot} AS result
# Did Luis Guzmán appear in any other movies?
MATCH (p:Person {name:"Luis Guzmán"})-[:ACTED_IN]->(movie)
RETURN {movie: movie.title} AS result
# Recommend a movie
MATCH (u:User {id: $userId})-[:LIKE_MOVIE]->(m:Movie)
MATCH (m)<-[r1:RATED]-()-[r2:RATED]->(otherMovie)
WHERE r1.rating > 3 AND r2.rating > 3 AND NOT EXISTS {(u)-[:WATCHED|LIKE_MOVIE|DISLIKE_MOVIE]->(otherMovie)}
WITH otherMovie, count(*) AS count
ORDER BY count DESC
LIMIT 1
RETURN {recommended_movie:otherMovie.title} AS result
"""


"""### Prompt for Generating Cypher Query by GPT-4 model"""
generating_cypher_prompt = f"""
You are an assistant with an ability to generate Cypher queries based off example Cypher queries.
Example Cypher queries are: \n {examples} \n
Do not response with any explanation or any other information except the Cypher query.
You do not ever apologize and strictly generate cypher statements based of the provided Cypher examples.
You need to update the database using an appropriate Cypher statement when a user mentions their likes or dislikes, or what they watched already.
Do not provide any Cypher statements that can't be inferred from Cypher examples.
Inform the user when you can't infer the cypher statement due to the lack of context of the conversation and state what is the missing context.
"""


"""### Prompt for Generating Final User Response"""
final_result_prompt = f"""
You are an assistant that helps to generate text to form nice and human understandable answers based.
The latest prompt contains the information, and you need to generate a human readable response based on the given information.
Make it sound like the information are coming from an AI assistant, but don't add any information.
Do not add any additional information that is not explicitly provided in the latest prompt.
I repeat, do not add any information that is not explicitly given.
"""


"""### Check for Valid Cypher Query"""
def is_cypher_query(query):
    try:
        with neo4j_session.session() as db:
            print(1)
            db.run(query)
            return True
    except Exception:
        print(2)
        return False


"""### Generate Final Response after getting data from the Database"""
def generate_response(user_input):
    messages = [
        {"role": "system", "content": final_result_prompt}
    ] # + user_input
    # Directly add the user_input or call the messages.append method
    messages.append({"role": "user", "content": user_input})

    # Make a request to OpenAI
    completions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.0
    )
    response = completions.choices[0].message.content
    messages.append({"role": "assistant", "content": response})
    # print(response)

    # If the model apologized, remove the first line or sentence
    # if "apologi" in response:
    #     if "\n" in response:
    #         response = " ".join(response.split("\n")[1:])
    #     else:
    #         response = " ".join(response.split(".")[1:])
    return response

# # Hardcoded UserID
# USER_ID = "Sanjay"

# # On the first execution, we have to create a user node in the database.
# db.run("""
#     MERGE (u:User {id: $userId})
#     """, {'userId': USER_ID})


def MovieChatbot(user_input):
    messages = [{"role": "system", "content": generating_cypher_prompt}]
    messages.append({"role": "user", "content": user_input})

    response = openai.ChatCompletion.create(
        model = "gpt-3.5-turbo",
        messages = messages,
        temperature=0.0
    )

    reply = response["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": reply})

    if "`" in reply:
        reply = reply.split("```")[1].strip("`")
    print(reply)
    if is_cypher_query(reply):
        with neo4j_session.session() as db:
            print(reply)
            docs = db.run(reply, params={})
            print(docs.data())

            response = [doc.values()[0] for doc in docs]
            print(response)
        if len(response) == 0:
                message = f"Apologise to the user as you don't have an information related to this particular movie or show."
                response = generate_response(message)
        else:
            response = generate_response(",".join(response))
    else:
        message = f"Greet the user and ask more information related to the Movie"
        response = generate_response(message)
        print(response)
    print(response)
    return response


"""### Gradio Initialization"""
inputs = gradio.Textbox(lines=7, label="Chat with Neo4jGPT")
outputs = gradio.Textbox(label="Neo4j Reply")
demo = gradio.Interface(fn=MovieChatbot, inputs=inputs, outputs=outputs, title="Movie Chatbot Backed by Neo4j")


"""### Launch Gradio bot"""
demo.launch(share=True)


"""### Close Gradio bot"""
# demo.close()
