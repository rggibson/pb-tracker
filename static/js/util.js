function set_boxart_if_exists( img_id, game_code ) {
    if( window.XMLHttpRequest ) {
	xhttp = new XMLHttpRequest( );
    } else {
	xhttp = new ActiveXObject( "Microsoft.XMLHTTP" );
    }
    xhttp.open( "GET", "/static/boxart/" + game_code + ".jpg", false );
    xhttp.send( ); 
    if( xhttp.status == 200 ) {
	var elem = document.getElementById( img_id );
	elem.setAttribute( "src", "/static/boxart/" + game_code + ".jpg" );
    }    
}

function set_img( img_id, img_src ) {
    if( img_src ) {
	var elem = document.getElementById( img_id );
	elem.setAttribute( "src", img_src );
    }
}

function block_double_submit( button_id ) {
    $( 'form' ).on( 'submit', function( ) {
	$( button_id ).button( 'loading' )
    } );
}
