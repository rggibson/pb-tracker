function set_boxart_if_exists( img_id, game_code ) {
    var img_url = "/static/boxart/" + game_code + ".jpg";
    $.ajax( {
	url: img_url,
	type: "HEAD",
	success: function() {
	    var elem = document.getElementById( img_id );
	    elem.setAttribute( "src", img_url ); 
	}
    } );
}

function set_img( img_id, img_src ) {
    if( img_src ) {
	$.ajax( {
	    url: img_src,
	    type: "HEAD",
	    success: function() {
		var elem = document.getElementById( img_id );
		elem.setAttribute( "src", img_src ); 
	    }
	} );
    }
}

function block_double_submit( button_id ) {
    $( 'form' ).on( 'submit', function( ) {
	$( button_id ).button( 'loading' )
    } );
}
