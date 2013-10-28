function block_double_submit( button_id ) {
    $( 'form' ).on( 'submit', function( ) {
	$( button_id ).button( 'loading' )
    } );
}

/* Returns a list of all keys in the Javascript object */
function keys( obj ) {
    var keys = [ ];
    for( var key in obj ) {
        if( obj.hasOwnProperty( key ) ) {
            keys.push(key);
        }
    }

    return keys;
}

function set_nav_return_urls( from, have_user ) {
    if( have_user ) {
	$( '#nav-logout-a' ).attr( "href", $( '#nav-logout-a' ).attr( "href" )
				   + "?from=" + from );	
    } else {
	$( '#nav-signup-a' ).attr( "href", $( '#nav-signup-a' ).attr( "href" )
				   + "?from=" + from );	
	$( '#nav-login-a' ).attr( "href", $( '#nav-login-a' ).attr( "href" )
				  + "?from=" + from );	
    }
}
