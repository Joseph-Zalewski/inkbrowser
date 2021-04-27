from SPARQLWrapper import SPARQLWrapper, JSON
import json

#plan: run sparql queries to retrieve a graph with positioning information
#then convert graph to JSON, in some modular way
#intermediate representation: adjacency list (di)graph - list of pairs of object/edge

XSCALE = 500
YSCALE = 500
SUBCLASS_OF = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
CURRENT_ID = 0

#takes a sparql endpoint holding comodide positioning data
def main(endpoint, queryEndpoint = ""):
    inter = []
    
    #stock graph with edges
    #get entity positions
    wrapper = SPARQLWrapper(endpoint)
    wrapper.setQuery("""PREFIX opla-sd: <http://ontologydesignpatterns.org/opla-sd#>
        SELECT ?N ?P ?X ?Y WHERE { ?N opla-sd:entityPosition ?P .
        ?P opla-sd:entityPositionX ?X . ?P opla-sd:entityPositionY ?Y}""")
    wrapper.setReturnFormat(JSON)
    results = wrapper.query().convert()

    #now that we have the query results in a dict, we build the abstract graph
    #format is: inter is a list of tuples of a node (URI string) and its adjacency list
    #and its x,y positions
    for binding in results["results"]["bindings"]:
        inter.append((binding["N"]["value"],[],float(binding["X"]["value"]),float(binding["Y"]["value"])))
    #normalize the positions
    xmax = 1
    ymax = 1
    for entry in inter:
        if entry[2] > xmax:
            xmax = entry[2]
        if entry[3] > ymax:
            ymax = entry[3]
    for i in range(len(inter)):
        inter[i] = (inter[i][0], inter[i][1], inter[i][2] * XSCALE / xmax, inter[i][3] * YSCALE / ymax)
    #get subclass edges
    for i in range(len(inter)):
        wrapper.setQuery("""PREFIX opla-sd: <http://ontologydesignpatterns.org/opla-sd#>
            SELECT ?O WHERE { <""" + inter[i][0] +
            """> <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?O .
            ?O opla-sd:entityPosition ?Q }""")
        wrapper.setReturnFormat(JSON)
        results = wrapper.query().convert()
        for binding in results["results"]["bindings"]:
            new_pair = (SUBCLASS_OF, binding["O"]["value"])
            inter[i][1].append(new_pair)
    #get property edges. CoModIDE stores these by default as OWL restrictions!
    #If P is an edge from D to R in the schema diagram, the OWL file will contain
    #D rdfs:subClassOf _:b0 . _:b0 owl:allValuesFrom R . _:b0 owl:onProperty P
    for i in range(len(inter)):
        wrapper.setQuery("""PREFIX opla-sd: <http://ontologydesignpatterns.org/opla-sd#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT ?P ?R WHERE { <""" + inter[i][0] +
            """> rdfs:subClassOf ?B . ?B owl:allValuesFrom ?R .
            ?B owl:onProperty ?P }""")
        wrapper.setReturnFormat(JSON)
        results = wrapper.query().convert()
        for binding in results["results"]["bindings"]:
            new_pair = (binding["P"]["value"], binding["R"]["value"])
            inter[i][1].append(new_pair)
    #now all edges should be in the abstract graph 'inter'

    #construct JSON output. This will be structured as a Python dict, and
    #then dumped to JSON.
    ret = {}
    ret["Boxes"] = []
    ret["Arrows"] = []
    ret["Mode"] = "DEFAULT"
    ret["CanvasX"] = XSCALE
    ret["CanvasY"] = YSCALE
    
    for n in inter:
        nBox = {};
        nBox["Id"] = n[0]
        nBox["XOffset"] = n[2]
        nBox["YOffset"] = n[3]
        nBox["XSize"] = getSize(n)[0]
        nBox["YSize"] = getSize(n)[1]
        nBox["FillColorHex"] = "#ffff00"
        nBox["TextColorHex"] = "#000000"
        nBox["Label"] = getNodeLabel(n)
        nBox["Query"] = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> SELECT ?X WHERE { ?X rdf:type <""" + n[0] + "> }"
        nBox["Limit"] = 50
        nBox["Endpoint"] = queryEndpoint
        ret["Boxes"].append(nBox)
        #iterate over the edges whose source is n
        for e in n[1]:
            eArr = {};
            eArr["Id"] = newID()
            eArr["Label"] = getEdgeLabel(e)
            if e[0] == SUBCLASS_OF:
                eArr["ArrowType"] = "Hollow"
            else:
                eArr["ArrowType"] = "Solid"
            eArr["Source"] = nBox["Id"]
            eArr["Target"] = e[1]
            ret["Arrows"].append(eArr)
            eArr["Query"] = "SELECT ?X ?Z WHERE { ?X <" + e[0] + "> ?Z }"
            eArr["Limit"] = 50
            eArr["Endpoint"] = queryEndpoint
            
    

    print(json.dumps(ret))


#takes a node of the abstract graph, and returns what its label should be
#in the schema diagram
def getNodeLabel(n):
        segments = n[0].split("#")
        return segments[len(segments)-1]

#takes an edge of the abstract graph, and returns what its label should be
#in the schema diagram
def getEdgeLabel(e):
        segments = e[0].split("#")
        return segments[len(segments)-1]

#takes a node of the abstract graph, and returns what its size should be
#in the schema diagram as a pair (x,y)
def getSize(n):
        return (100,100)

def newID():
    global CURRENT_ID
    CURRENT_ID = CURRENT_ID + 1
    return CURRENT_ID
        


















