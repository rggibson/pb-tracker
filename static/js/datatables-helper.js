/* Special function for datatables.  See datatables.net */
function strip( html ) {
    var tmp = document.createElement("DIV");
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || "";
}

function timestr_to_secs( timestr ) {
    /* Must strip out html tags before split */
    timetext = strip( timestr );
    var parts = timetext.split( ":" );
    if( parts.length == 1 ) {
	return parseFloat( parts[ 0 ], 10 );
    } else if( parts.length == 2 ) {
	return ( 60 * parseFloat( parts[ 0 ], 10 ) ) 
	    + parseFloat( parts[ 1 ], 10 );
    } else { 
	return ( 3600 * parseFloat( parts[ 0 ], 10 ) ) 
	    + ( 60 * parseFloat( parts[ 1 ], 10 ) ) + parseFloat( parts[ 2 ], 10 );
    }
}

jQuery.fn.dataTableExt.oSort['time-asc'] = function( x, y ) {
    var x_secs = timestr_to_secs( x );
    var y_secs = timestr_to_secs( y );
    return ( ( x_secs < y_secs ) ? -1 : ( ( x_secs > y_secs ) ? 1 : 0 ) );
};

jQuery.fn.dataTableExt.oSort['time-desc'] = function( x, y ) {
    var x_secs = timestr_to_secs( x );
    var y_secs = timestr_to_secs( y );
    return ( ( x_secs < y_secs ) ? 1 : ( ( x_secs > y_secs ) ? -1 : 0 ) );
};

var month_to_int = { 
    "Jan": 0,
    "Feb": 1,
    "Mar": 2,
    "Apr": 3,
    "May": 4,
    "Jun": 5,
    "Jul": 6,
    "Aug": 7,
    "Sep": 8,
    "Oct": 9,
    "Nov": 10,
    "Dec": 11 };

jQuery.fn.dataTableExt.oSort['mydate-asc'] = function( x, y ) {
    var x_parts = x.split( " " );
    var y_parts = y.split( " " );
    if( x_parts.length < 3 ) {
	return ( ( y_parts.length < 3 ) ? 0 : -1 );
    } else if( y_parts.length < 3 ) {
	return 1;
    }

    if( x_parts.length >= 4 ) {
	var x_date = [ x_parts[ 3 ], month_to_int[ x_parts[ 1 ] ], 
		       x_parts[ 2 ] ];
    } else {
	var x_date = [ x_parts[ 2 ], month_to_int[ x_parts[ 0 ] ],
		       x_parts[ 1 ] ];
    }
    if( y_parts.length >= 4 ) {
	var y_date = [ y_parts[ 3 ], month_to_int[ y_parts[ 1 ] ], 
		       y_parts[ 2 ] ];
    } else {
	var y_date = [ y_parts[ 2 ], month_to_int[ y_parts[ 0 ] ],
		       y_parts[ 1 ] ];
    }
    for( var i = 0; i < x_date.length; ++i ) {
	if( x_date[ i ] != y_date[ i ] ) {
	    return ( ( x_date[ i ] < y_date[ i ] ) ? -1 : 1 );
	}
    }

    return 0;
};

jQuery.fn.dataTableExt.oSort['mydate-desc'] = function( x, y ) {
    var x_parts = x.split( " " );
    var y_parts = y.split( " " );
    if( x_parts.length < 3 ) {
	return ( ( y_parts.length < 3 ) ? 0 : 1 );
    } else if( y_parts.length < 3 ) {
	return -1;
    }

    if( x_parts.length >= 4 ) {
	var x_date = [ x_parts[ 3 ], month_to_int[ x_parts[ 1 ] ], 
		       x_parts[ 2 ] ]; 
    } else {
	var x_date = [ x_parts[ 2 ], month_to_int[ x_parts[ 0 ] ], 
		       x_parts[ 1 ] ]; 
    }
    if( y_parts.length >= 4 ) {
	var y_date = [ y_parts[ 3 ], month_to_int[ y_parts[ 1 ] ], 
		       y_parts[ 2 ] ];
    } else {
	var y_date = [ y_parts[ 2 ], month_to_int[ y_parts[ 0 ] ], 
		       y_parts[ 1 ] ];
    }
    for( var i = 0; i < x_date.length; ++i ) {
	if( x_date[ i ] != y_date[ i ] ) {
	    return ( ( x_date[ i ] < y_date[ i ] ) ? 1 : -1 );
	}
    }

    return 0;
};
