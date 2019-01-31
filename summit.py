import chinese_postman_lib as cpl
import networkx

def summit_fixes(g):

  edges_to_purge = []
  for n1, n2 in g.edges_iter():
    if (not g[n1][n2].get('name')) or (g[n1][n2].get('highway') == 'path'):
      edges_to_purge.append((n1, n2))
  for n1, n2 in edges_to_purge:
     g.remove_edge(n1, n2)

  nodes_to_purge = []
  for node in g:
    streets = cpl.adjoining_streets(g, node)
    lon, lat = g.node[node].get('coordinate')
    # All of these are points where streets cross into other towns, and I
    # eliminate points in order to cut off routes into other towns.
    # I am writing these in clockwise order from where Morris Avenue crosses
    # NJ-24 into Springfield.
    if (('Morris Avenue' in streets and lon > -74.331090) or
        # What lines of this form are saying is that you can be on the
        # intersection of the two, but you can't otherwise be on Briant Park
        # Drive. If I eliminated ALL Briant Park Drive points, I'd be severing
        # Springfield Avenue and disconnecting parts of Summit.
        ('Briant Park Drive' in streets and 'Springfield Avenue' not in streets) or
        ('Orchard Street' in streets and lon > -74.338021) or
#        ('McCallum Street' in streets and lat < 40.054860) or
#        ('Rex Avenue' in streets and lon < -75.220668) or
        ('Shunpike Road' in streets and lon > -74.339555) or
        ('Summit Road' in streets and lat < 40.700385) or
        ('W. R. Tracy Drive' in streets and lon > -74.370068) or
        ('Glenside Avenue' in streets and lat < 40.688211) or
        ('Winchip Road' in streets and lon < -74.381843) or
        ('Glenside Avenue' in streets and lat < 40.688211) or
        # If you're going west on Club Drive, Club Lane is where you can assume
        # you've left Summit.
        ('Club Lane' in streets) or
        ('Mountain Avenue' in streets and lon < -74.384198) or
        # See below for the Division Avenue border.
        ('Springfield Avenue' in streets and lon < -74.387309) or
        ('Mount Vernon Avenue' in streets and lon < -74.391220) or
        ('Stanley Avenue' in streets and lat > 40.726245) or
        ('Watchung Avenue' in streets and lon < -74.379313) or
        ('Summit Avenue' in streets and lat > 40.733164) or
        ('John F. Kennedy Parkway' in streets and lat > 40.739859) or
        ('Main Street' in streets and lon < -74.371891) or
        ('Hobart Gap Road' in streets and 'Hobart Avenue' not in streets) or
        ('Overhill Road' in streets and 'Mountain Avenue' not in streets) or
        # Old Coach isn't in the tax map so I am declaring it not a real street.
        ('Old Coach Road' in streets and 'Baltusrol Road' not in streets) or
        # See below for Morris Turnpike border.
        ('Morris Turnpike' in streets and lon > -74.331790)):
       nodes_to_purge.append(node)
    elif 'Division Avenue' in streets:
      # Anything emerging from Division Avenue to the west is in Berkeley
      # Heights or New Providence. Except for that one stretch of Old
      # Avenue.
      for neighbor in g[node]:
        neighbor_streets = cpl.adjoining_streets(g, neighbor)
        if 'Division Avenue' not in neighbor_streets and 'Old Springfield Avenue' not in neighbor_streets and cpl.longitude(g, neighbor) < lon:
          print "DEBUG: I will purge node %s (%s,%s) on %s because it is west from Division Avenue node %s (%s,%s)." % (neighbor, cpl.latitude(g, neighbor), cpl.longitude(g, neighbor), neighbor_streets, node, lat, lon)
          nodes_to_purge.append(neighbor)
    elif 'Morris Turnpike' in streets:
      # Anything emerging from Morris Turnpike to the north is Springfield or
      # Millburn.
      for neighbor in g[node]:
        neighbor_streets = cpl.adjoining_streets(g, neighbor)
        if 'Morris Turnpike' not in neighbor_streets and cpl.latitude(g, neighbor) > lat:
          print "DEBUG: I will purge node %s (%s,%s) on %s because it is north from Morris Turnpike node %s (%s,%s)." % (neighbor, cpl.latitude(g, neighbor), cpl.longitude(g, neighbor), neighbor_streets, node, lat, lon)
          nodes_to_purge.append(neighbor)

  for node in set(nodes_to_purge):
    g.remove_node(node)

  # Having cut off the borders, we cull everything unreachable from within the
  # borders.
  town_nodes = set(networkx.dfs_preorder_nodes(g, 105432048))
  non_town_nodes = set(g.nodes()) - town_nodes
  for node in non_town_nodes:
    g.remove_node(node)

summit_filename="/home/mark/git/chinese_postman/data/summit_all.osm"

make_summit = lambda: cpl.make_graphs([summit_filename], summit_fixes)

if __name__ == '__main__':
  pure_g, reduced_g = make_summit()
  eulerian_graph = cpl.add_edges_for_euler(pure_g, reduced_g)
  cpl.get_and_format_circuit(eulerian_graph, 105432048)

