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
