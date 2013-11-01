function timestr_to_secs( timestr ) {
    var parts = timestr.split( ":" );
    if( parts.length == 1 ) {
	return parseInt( parts[ 0 ], 10 );
    } else if( parts.length == 2 ) {
	return ( 60 * parseInt( parts[ 0 ], 10 ) ) 
	    + parseInt( parts[ 1 ], 10 );
    } else { 
	return ( 3600 * parseInt( parts[ 0 ], 10 ) ) 
	    + ( 60 * parseInt( parts[ 1 ], 10 ) ) + parseInt( parts[ 2 ], 10 );
    }
}

jQuery.fn.dataTableExt.oSort['time-asc'] = function( x, y ) {
    x_secs = timestr_to_secs( x );
    y_secs = timestr_to_secs( y );
    return ( ( x_secs < y_secs ) ? -1 : ( ( x_secs > y_secs ) ? 1 : 0 ) );
};

jQuery.fn.dataTableExt.oSort['time-desc'] = function( x, y ) {
    x_secs = timestr_to_secs( x );
    y_secs = timestr_to_secs( y );
    return ( ( x_secs < y_secs ) ? 1 : ( ( x_secs > y_secs ) ? -1 : 0 ) );
};
