# xmlpage.py
# Author: Richard Gibson
#
# Renders a page generated from an xml file.  Currently renders /faq and /blog
#

import handler
import urllib2
import xml.etree.cElementTree as et

class XmlPage( handler.Handler ):
    def get( self ):
        user = self.get_user( )

        # Grab the optional query parameter and cast it as an int.
        # Currently only used for /faq
        q = self.request.get( 'q' )
        try:
            q = int( q )
        except ValueError:
            pass

        # Get the name of the xml file from the URL path
        path = self.request.path 
        if path.endswith('/'):
            path = path[:-1] # Should now be, for example, '/faq' or '/blog'

        # Read the xml file and store in a string
        f = open( 'xml' + path + '.xml', 'r' )
        tree = et.fromstring( f.read( ) )
        f.close( )

        # Build the list of dictionaries of lists from the xml file
        xml = [ ]
        for child in tree.findall( path[ 1: ] ):
            d = dict( )
            xml.append( d )
            for item in child:
                if d.get( item.tag ) is None:
                    d[ item.tag ] = [ item.text ]
                else:
                    d[ item.tag ].append( item.text )

        self.render( path[ 1: ] + ".html", user=user, xml=xml, q=q )
