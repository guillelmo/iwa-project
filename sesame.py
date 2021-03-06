#Library with methods for accessing the Sesame triplestore

import urlfetch
import urllib
from django.utils import simplejson as json
from operator import itemgetter

from rdflib.graph import ConjunctiveGraph
from rdflib.term import URIRef, Literal
from rdflib.namespace import Namespace, RDF, RDFS, XSD

rdfStoreUrl = 'http://ec2-46-51-144-109.eu-west-1.compute.amazonaws.com:8080/openrdf-sesame/repositories/iwaproj'
#rdfStoreUrl = 'http://localhost:8081/openrdf-sesame/repositories/iwaproj'

#Obtains the dbPedia entry corresponding to the mb_id (Music Brain ID)
def getDbPediaEntry(mb_id): 

   endPoint = rdfStoreUrl + "?"
   
   query = """PREFIX dbpedia-owl:<http://www.w3.org/2002/07/owl#>

   SELECT DISTINCT ?db_entry
   WHERE {
   ?db_entry dbpedia-owl:sameAs %s
   }""" % ('<http://zitgist.com/music/artist/'+mb_id+'>')
   
   res = queryRdfStore(endPoint, query)
   if len(res) > 0:
      return res[0]['db_entry']
   else:
      return None

def matchEvents(username,city):

   query = """
   PREFIX ns2:<http://iwa2012-18-project.appspot.com/>
   PREFIX ns1:<http://iwa2012-18-project.appspot.com/event/>
   PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
   PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
   
   SELECT DISTINCT ?eventid ?event ?date
   WHERE {
   ?eventid ns1:artist ?artistURI .
   <http://iwa2012-18-project.appspot.com/lastfm/%s> ns2:likesArtist ?artistURI .
   ?eventid rdfs:label ?event .
   ?eventid ns1:onDate ?date .
   ?eventid ns1:city <http://dbpedia.org/resource/%s> .
   }
   """ % (username, city)

   endPoint = rdfStoreUrl + "?"

   response = queryRdfStore(endPoint, query)

   res = []
   resIndex = 0

   for row in response:
       event = []
       eventIndex = 0
       for key,value in row.iteritems():
           event.insert(eventIndex,value)
           eventIndex += 1
           res.insert(resIndex, event)
           resIndex += 1           
   return res

def getRecommendations(username, city):

    query = """
    PREFIX ns2:<http://iwa2012-18-project.appspot.com/>
    PREFIX ns1:<http://iwa2012-18-project.appspot.com/event/>
    PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?eventid ?event ?date
    WHERE {
    ?eventid ns1:artist ?artistURI .
    ?eventid ns1:genre ?genre .
    <http://iwa2012-18-project.appspot.com/lastfm/%s> ns2:likesGenre ?genre .
    ?eventid rdfs:label ?event .
    ?eventid ns1:onDate ?date .
    ?eventid ns1:city <http://dbpedia.org/resource/%s> .
    }
    """ % (username, city)

    endPoint = rdfStoreUrl + "?"

    response = queryRdfStore(endPoint, query)

    res = []
    resIndex = 0

    for row in response:
        event = []
        eventIndex = 0
        for key,value in row.iteritems():
            event.insert(eventIndex,value)
            eventIndex += 1
        res.insert(resIndex, event)
        resIndex += 1

    return res

def appendArtistToFilter(dbEntryUrl, last=False):
   if(last):
      return " ?artist = <"+dbEntryUrl + "> "
   else:
      return " ?artist = <"+dbEntryUrl + "> || "
  
def getGenres(artists, nrOfGenres):

   artist_filter = ''
   
   for rank,artist in enumerate(artists):

      entry = None
      
      if(artist['mbid']):
         entry = getDbPediaEntry(artist['mbid'])
         
      if(not entry):
         #print "NOT Entry : "+artist['name']
         entry = "http://dbpedia.org/resource/"+artist['name'].replace(" ","_")
         
      artist_filter += appendArtistToFilter(entry, (rank==(len(artists)-1)))
      
   query = """PREFIX dbpedia-owl: <http://dbpedia.org/property/>
   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

   SELECT ?genre
   WHERE {
   { ?artist dbpedia-owl:genre ?genreURI.
   ?genreURI rdfs:label ?genre .
   FILTER (langMatches(lang(?genre), 'en')) }
   FILTER (%s)
   
   }
   """ % (artist_filter)
       
   endpoint = "http://dbpedia.org/sparql?"

   response = queryRdfStore(endpoint,query)
    
   res = []
   resindex = 0
   
   for row in response:
 
      for key,value in row.iteritems():
           res.insert(resindex,value)
           resindex += 1

   resCounted = [(a, res.count(a)) for a in set(res)]
   resSorted = sorted(resCounted, key=itemgetter(1), reverse=True)

   genreIndex = 0
   genres = []

   for item in resSorted:
      if genreIndex == nrOfGenres:
         break
      genres.insert(genreIndex, item[0])
      genreIndex += 1
      
   return genres

def findEventGenres(artistName):

    res = []

    query = """
    PREFIX dbpedia-owl: <http://dbpedia.org/property/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?genre
    WHERE {
    { <http://dbpedia.org/resource/%s> dbpedia-owl:genre ?genreURI.
    ?genreURI rdfs:label ?genre .
    FILTER (langMatches(lang(?genre), 'en')) }
    }
    """ % (artistName.replace(" ","_"))

    endpoint = "http://dbpedia.org/sparql?"

    response = queryRdfStore(endpoint,query)
    
    resindex = 0

    for row in response:
        for key,value in row.iteritems():
            res.insert(resindex,value)
            resindex += 1

    return res

def getArtistCard(mb_id):

   #http://www.bbc.co.uk/music/artists/309c62ba-7a22-4277-9f67-4a162526d18a#artist
   endpoint = "http://api.talis.com/stores/bbc-backstage/services/sparql?"
   query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
   PREFIX dc: <http://purl.org/dc/elements/1.1/>
   PREFIX foaf: <http://xmlns.com/foaf/0.1/>
   PREFIX mo: <http://purl.org/ontology/mo/>
   PREFIX rel: <http://purl.org/vocab/relationship/>
   PREFIX rev: <http://purl.org/stuff/rev#>
   SELECT ?rev ?title ?author ?album_mbid ?text WHERE {
    
   ?rev a rev:Review;
   rev:reviewer ?person;
   foaf:primaryTopic ?record. 
   
   ?person foaf:name ?author.
   ?rev rev:title ?title. 
    
   ?record mo:musicbrainz ?album_mbid; 
   foaf:maker <http://www.bbc.co.uk/music/artists/%s#artist>.
   
   ?rev rev:text ?text.
   }""" % (mb_id)
   #print endpoint
   #print query
   response = queryRdfStore(endpoint, query)
   return response

def createRDF(username, city, artists, locationInformation, events, genres):

    graph = ConjunctiveGraph()

    rdfs = Namespace('http://www.w3.org/2000/01/rdf-schema#')
    iwa = Namespace('http://iwa2012-18-project.appspot.com/')
    lfm = Namespace('http://iwa2012-18-project.appspot.com/lastfm/')
    ev = Namespace('http://iwa2012-18-project.appspot.com/event/')
    dbp = Namespace('http://dbpedia.org/resource/') # DBPedia link to artists, genres and cities
    
    for artist in artists:

        graph.add(( lfm[username], iwa['likesArtist'], dbp[artist['name'].replace(" ","_")] ))
        graph.add(( dbp[artist['name'].replace(" ","_")], rdfs['label'], Literal(artist['name']) ))

    for location in locationInformation:

        graph.add(( dbp[city.replace(" ","_")], iwa['poi'], Literal(location) ))

    for event in events:

        try:
            graph.add(( ev[event[0]], ev['onDate'], Literal(str(event[1].year)+"-"+str(event[1].month)+"-"+str(event[1].day),datatype=XSD.date) ))
            graph.add(( ev[event[0]], rdfs['label'], Literal(event[2]) ))
            graph.add(( ev[event[0]], ev['artist'], dbp[event[3].replace(" ","_")] ))
            graph.add(( ev[event[0]], ev['venue'], Literal(event[4]) ))
            graph.add(( ev[event[0]], ev['city'], dbp[city.replace(" ","_")] ))

            for eventGenre in event[5]:

                graph.add(( ev[event[0]], ev['genre'], dbp[eventGenre.replace(" ","_")] ))

        except AttributeError:
            graph.add(( ev[event[0]], rdfs['label'], Literal("Event is missing information") ))

    for genre in genres:

        graph.add(( lfm[username], iwa['likesGenre'], dbp[genre.replace(" ","_")] ))
        graph.add(( dbp[genre.replace(" ","_")], rdfs['label'], Literal(genre) ))

    graph.add(( dbp[city.replace(" ","_")], rdfs['label'], Literal(city) ))

    return graph

def storeRDF(graph):

    data=graph.serialize(format='xml')    
    url = rdfStoreUrl + "/statements"

    jsonresult = urlfetch.fetch(url,payload=data,deadline=30,method=urlfetch.POST, headers={ 'content-type': 'application/rdf+xml'})

def queryRdfStore(endPoint, query):

    try:
        url = endPoint + urllib.urlencode({"query" : query})

    except UnicodeEncodeError:
        return ""

    #print url
    jsonresult = urlfetch.fetch(url,deadline=30,method=urlfetch.GET, headers={"accept" : "application/sparql-results+json"})

    if(jsonresult.status_code == 200):
       res = json.loads(jsonresult.content)
       
       res_var = res['head']['vars']
        
       response = []
       for row in res['results']['bindings']:
          dic = {}
          
          for var in res_var:
             dic[var] = row[var]['value']

          response.append(dic)
                        
       return response    
    else:
       return {"error" : jsonresult.content} 
