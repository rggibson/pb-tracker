# faq.py
# Author: Richard Gibson
#
# Renders frequently asked questions from an xml file. 
#

import handler
import urllib2
import xml.etree.cElementTree as et

class Faq( handler.Handler ):
    def get( self ):
        user = self.get_user( )

        # Check to see if we should start with one of the faqs visible
        q = self.request.get( 'q' )
        try:
            q = int( q )
        except ValueError:
            pass

        # Read the xml file and store in a string
        f = open( 'xml/faq.xml', 'r' )
        tree = et.fromstring( f.read( ) )
        f.close( )

        # Building the list of dictionaries
        faqs = [ ]
        for child in tree.findall( 'faq' ):
            faq = dict( )
            faqs.append( faq )
            for item in child:
                faq[ item.tag ] = item.text

        self.render( "faq.html", user=user, faqs=faqs, q=q )
