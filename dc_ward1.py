import chinese_postman_lib as cpl
import geog
import networkx
import osmgraph

def edge_goes_direction_off_street(g, n1, n2, direction, border):
  if g[n1][n2].get('name') == border:
    return False
  streets1 = cpl.adjoining_streets(g, n1)
  streets2 = cpl.adjoining_streets(g, n2)
  if (border in streets1) == (border in streets2):
    return False
  if border in streets1:
    border_node = n1
    other_node = n2
  else:
    border_node = n2
    other_node = n1
  border_lon, border_lat = g.node[border_node].get('coordinate')
  other_lon, other_lat = g.node[other_node].get('coordinate')
  if direction == 'west':
    return other_lon < border_lon
  if direction == 'east':
    return other_lon > border_lon
  if direction == 'north':
    return other_lat > border_lat
  if direction == 'south':
    return other_lat < border_lat
  raise "Invalid direction: %s" % direction

def dc_fixes(g):
  bad_road_types = set(['residential', 'service'])
  streets_to_skip = set(['11th St Alley',
                         '15th Street Northwest Cycle Track',
                         'Piney Branch Trail',
                         'Valley Trail',
                        ])
  edges_to_purge = []
  edges_to_rename = {
    # TODO: Fix all of these in Open Street Map.
    'Belmont Rd NW': 'Belmont Road Northwest',
    'Bryant Street': 'Bryant Street Northwest',
    'Florida Ave NW' : 'Florida Avenue Northwest',
    'Howard Pl NW': 'Howard Place Northwest',
    'Lamont St NW': 'Lamont Street Northwest',
    'Monroe St NW': 'Monroe Street Northwest',
    'Mozart Pl NW' : 'Mozart Place Northwest',
    'Oak St NW' : 'Oak Street Northwest',
    'Ontario Rd NW': 'Ontario Road Northwest',
    'Spring Place' : 'Spring Place Northwest',
    }

  for n1, n2 in g.edges_iter():
    if ((not g[n1][n2].get('name')) or
        g[n1][n2].get('name') in streets_to_skip):
        # and (g[n1][n2].get('highway') in bad_road_types):
      edges_to_purge.append((n1, n2))
    if g[n1][n2].get('name') in edges_to_rename:
      old_name = g[n1][n2]['name']
      g[n1][n2]['name'] = edges_to_rename[old_name]

    lon1, lat1 = g.node[n1].get('coordinate')
    if (edge_goes_direction_off_street(g, n1, n2, 'west', 'Connecticut Avenue Northwest') or
        (edge_goes_direction_off_street(g, n1, n2, 'north', 'Spring Road Northwest') and lon1 < -77.025532) or
        # TODO: Figure out why 1021561599 is listed as "dead end" when it's
        # still connected to 49776943.
        (edge_goes_direction_off_street(g, n1, n2, 'west', 'New Hampshire Avenue Northwest') and lat1 > 38.935466) or
        (edge_goes_direction_off_street(g, n1, n2, 'north', 'Rock Creek Church Road Northwest') and lat1 > 38.935328) or
        # East from Park Place north of Michigan Ave but we have to exclude that
        # one weird spot where Park Place becomes TWO PARK PLACES, or else we
        # will cut off a legitimate piece of Rock Creek Church Road.
        (edge_goes_direction_off_street(g, n1, n2, 'east', 'Park Place Northwest') and ((lat1 > 38.928931 and lat1 < 38.936678) or (lat1 > 38.9373))) or
        (edge_goes_direction_off_street(g, n1, n2, 'north', 'Michigan Avenue Northwest') and lon1 > -77.018030) or
        edge_goes_direction_off_street(g, n1, n2, 'east', '1st Street Northwest') or
        edge_goes_direction_off_street(g, n1, n2, 'east', '2nd Street Northwest') or
        edge_goes_direction_off_street(g, n1, n2, 'south', 'Rhode Island Avenue Northwest') or
        (edge_goes_direction_off_street(g, n1, n2, 'south', 'Florida Avenue Northwest') and lon1 > -77.020592) or
        edge_goes_direction_off_street(g, n1, n2, 'south', 'S Street Northwest') or
        (edge_goes_direction_off_street(g, n1, n2, 'west', '14th Street Northwest') and lat1 < 38.916850) or
        (edge_goes_direction_off_street(g, n1, n2, 'south', 'U Street Northwest') and lon1 > -77.040668 and lon1 < -77.032636) or
        (edge_goes_direction_off_street(g, n1, n2, 'south', 'Florida Avenue Northwest') and lon1 > -77.043839 and lon1 < -77.041453) or
        (edge_goes_direction_off_street(g, n1, n2, 'south', 'Florida Avenue Northwest') and lon1 < -77.044568) or
        (edge_goes_direction_off_street(g, n1, n2, 'east', 'Florida Avenue Northwest') and lon1 < -77.041453)
        ):
      edges_to_purge.append((n1, n2))
  
  for n1, n2 in set(edges_to_purge):
    g.remove_edge(n1, n2)

  # 49821049 is on a weird offshoot of Connecticut Ave that goes outside the
  # ward.
  nodes_to_purge = [49821049]
  for node in g:
    streets = cpl.adjoining_streets(g, node)
    lon, lat = g.node[node].get('coordinate')
    if (('Rock Creek Trail' in streets and lat > 38.933061) or
        ('Connecticut Avenue Northwest' in streets and lon < -77.050140) or
        ('Calvert Street Northwest' in streets and lon < -77.048509) or
        ('1st Street Northwest' in streets and lat < 38.921247) or
        ('S Street Northwest' in streets and lon > -77.020756) or
        ('Beach Drive Northwest' in streets and lon < -77.048509)):
      nodes_to_purge.append(node)
  for node in set(nodes_to_purge):
    g.remove_node(node)

  # Having cut off the borders, we cull everything unreachable from within the
  # borders.
  ward1_nodes = set(networkx.dfs_preorder_nodes(g, 49745335))
  non_ward1_nodes = set(g.nodes()) - ward1_nodes
  for node in non_ward1_nodes:
    g.remove_node(node)

  for n1, n2 in g.edges_iter():
    c1, c2 = osmgraph.tools.coordinates(g, (n1, n2))   
    g[n1][n2]['length'] = geog.distance(c1, c2)

  return g

pure_g, g = cpl.make_graphs(
  ["/home/mark/git/chinese_postman/data/dc_ward1_sw.osm",
   "/home/mark/git/chinese_postman/data/dc_ward1_se.osm",
   "/home/mark/git/chinese_postman/data/dc_ward1_nw.osm",
   "/home/mark/git/chinese_postman/data/dc_ward1_ne.osm"],
  dc_fixes)

eulerian_graph = cpl.add_edges_for_euler(pure_g, g)
cpl.get_and_format_circuit(eulerian_graph, 49745335)

# Various things I've been using for debugging. I'll leave them here in case
# I need them again.
#cpl.print_contiguous_streets(g)
#path = networkx.dijkstra_path(g, 49770715, 647053797, weight='length')
#print [(pn, g.node[pn]['pretty_name']) for pn in path]

#for node in g:
#  streets = cpl.adjoining_streets(g, node)
#  if 'Quincy Street Northwest' in streets:
#    print "Valley Trail definitely touches node %s" % node
#    path = networkx.dijkstra_path(g, 49770715, node, weight='length')
#    print [(pn, g.node[pn]['pretty_name']) for pn in path]
#  else:
#    if node == 271392805:
#      print "Why the fuck do I think Valley Trail is not in the streets"
#for n1, n2 in g.edges_iter():
#  if cpl.get_edge_somehow(g, n1, n2).get('name') == 'Valley Trail':
#    print n1, g.node[n1]['pretty_name'], n2, g.node[n2]['pretty_name']
# 49809789 = 5th & U
# 455299376 = great cats
