function block_double_submit( button_id ) {
    $( 'form' ).on( 'submit', function( ) {
	$( button_id ).button( 'loading' )
    } );
}
