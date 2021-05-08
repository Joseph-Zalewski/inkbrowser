from SPARQLWrapper import SPARQLWrapper, JSON
import json

#plan: run sparql queries to retrieve a graph with positioning information
#then convert graph to JSON, in some modular way
#intermediate representation: adjacency list (di)graph - list of pairs of
#object/edge

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
    wrapper.setQuery("""PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX opla-sd: <http://ontologydesignpatterns.org/opla-sd#>
        SELECT ?N ?P ?X ?Y WHERE { ?N opla-sd:entityPosition ?P .
        ?P opla-sd:entityPositionX ?X . ?P opla-sd:entityPositionY ?Y
  			FILTER NOT EXISTS { ?N rdf:type owl:DatatypeProperty }
        }""")
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

    #Get remaining property edges! Sometimes these are stored not as restrictions
    #but as rdfs:domain and rdfs:range triples.
    for i in range(len(inter)):
        wrapper.setQuery("""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?P ?R WHERE { ?P rdfs:domain <""" + inter[i][0] +
            """> . ?P rdfs:range ?R }""")
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
            eArr["Query"] = "SELECT ?X ?Z WHERE { ?X <" + e[0] + "> ?Z }"
            eArr["Limit"] = 50
            eArr["Endpoint"] = queryEndpoint
            ret["Arrows"].append(eArr)
    #by default, no arrow waypoints have been set. However, we want to set them for
    #edges with shared domain and range, because the default mxGraph behavior for those
    #is to overlay them.
    for i in range(len(ret["Arrows"])):
            for j in range(i):
                e = ret["Arrows"][i]
                f = ret["Arrows"][j]
                if e["Source"] == f["Target"] and f["Source"] == e["Target"]:
                    se = getSource(e, ret)
                    sf = getSource(f, ret)
                    d = deOverlay(se["XOffset"], se["YOffset"], se["XSize"], se["YSize"], sf["XOffset"], sf["YOffset"], sf["XSize"], sf["YSize"])
                    e["Waypoints"] = d[0]
                    f["Waypoints"] = d[1]
    

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
        return (5*len(getNodeLabel(n)) + 20, 30)

#takes positions, x and y sizes of source and target for two contrary arrows.
#returns a pair containing waypoints for each.
def deOverlay(x1,y1,xs1,ys1,x2,y2,xs2,ys2):
    #get centroids
    xc1 = x1 + xs1/2
    yc1 = y1 + ys1/2
    xc2 = x2 + xs2/2
    yc2 = y2 + ys2/2
    #get vector from c1 to c2
    vx = xc2 - xc1
    vy = yc2 - yc1
    #get orthogonal vector to v
    ux = -vy
    uy = vx
    #create a "diamond" shape - waypoints are displaced by +- 1/2 u from the midpoint of v
    xw1 = xc1 + vx/2 + ux/2
    yw1 = yc1 + vy/2 + uy/2
    xw2 = xc1 + vx/2 - ux/2
    yw2 = yc1 + vy/2 - uy/2
    return ([(xw1,yw1)],[(xw2,yw2)])

#gets the Box that is the source of arrow e, according to pre-JSON representation rep
def getSource(e, rep):
    for B in rep["Boxes"]:
        if B["Id"] == e["Source"]:
            return B
    

def newID():
    global CURRENT_ID
    CURRENT_ID = CURRENT_ID + 1
    return CURRENT_ID
        


















