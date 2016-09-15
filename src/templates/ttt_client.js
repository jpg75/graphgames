const cards_colors = {"2H": "red", "3H": "red", "4H": "red",
                    "2C": "black", "3C": "black", "4C": "black"};
const cards_figs = {"2H": "2H.png", "3H": "3H.png", "4H": "4H.png",
                    "2C": "2C.png", "3C": "3C.png", "4C": "4C.png"};
const allowed_moving_zones = ["U", "T", "C", "N"];

let player = 'CK', score = 0, gameCard = '2H';
let username = '';

let socket = null; 
/* let socket = io.connect('http://' + document.domain + ':' + location.port);
socket.on('connect', function() {
    //socket.emit('my event', {data: 'I\'m connected!'});
	console.log('Connected to server @ '+document.domain +':'+location.port);
});

socket.on('hand', handleHand());
*/

$(document).ready(function () {
	/* initial card positions:
	NK    N   UP   C    CK   T	GC	PL
	3C   4H   2H   3H   2C   4C	2H	ck
	*/
	window.startPos = window.endPos = {};
	  
	initCardsData();
	makeDraggable();
	login();

    $('.cardSlot').droppable({
    	hoverClass: 'hoverClass',
        
        drop: function(event, ui) {
        	let $from = $(ui.draggable),
            	$fromParent = $from.parent(),
            	$to = $(this).children(),
              	$toParent = $(this);

			legal_move = checkMove($from, $fromParent, $to, $toParent);
			console.log("Is legal: "+ legal_move);
			
			if (!legal_move) {
				// restore the moved card to its previous position:
				window.endPos = $from.offset();
				swap($from, window.endPos, window.startPos, 500, function() {
            		$toParent.html($to.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            		$fromParent.html($from.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            		makeDraggable();
          		});
			}
			else {			
				// Invert the players when an exchange is legal: 
				// the parent objects are different
				if (! $toParent.is($fromParent) && legal_move) {
					invertPlayers($fromParent);
		  		}

				window.endPos = $to.offset();

				swap($from, $from.offset(), window.endPos, 200);
    	      	swap($to, window.endPos, window.startPos, 500, function() {
        	    	$toParent.html($from.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            		$fromParent.html($to.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            		makeDraggable();
          		});

          		score++;
          	}
	    }
	});
	  
	function swap($el, fromPos, toPos, duration, callback) {
		$el.css('position', 'absolute')
        	.css(fromPos)
        	.animate(toPos, duration, function() {
            	if (callback) callback();
          	});
	}
});

/**
* Make every card draggable, but disabled. Only the card's current player is made 
enabled and emphasized.
*/
function makeDraggable() {
	let checkedValue = document.getElementById("limitDrag").checked;
	console.log(checkedValue); 

    $('.card').draggable({
    	disabled: true,
    	containment: '#content',
    	zIndex: 99999,
    	revert: 'invalid',
    	start: function(event, ui) {
    		window.startPos = $(this).offset();
    	}
    });

	/* Enable the draggable(s) corresponding to the NK or CK cards*/
	$('#'+player+ '> .card').draggable('enable');
	emphasizeActivePlayer();
	initCardsData();
}

/*******************************************************************
* Game related functions
*/

/**
* Generate a sort of metadata inside the card slots
*/ 
function initCardsData(){
	$('.card').each(function(index, el) {
		let key = $(this).children().attr("src").slice(-6, -4);

		console.log('key: '+key);
		$(this).data('color', cards_colors[key] );
		console.log( index + ": " + $( this ).data('color') );
		$(this).data('number', key.charAt(0) );
		$(this).data('card', key );
		console.log( index + ": " + $( this ).data('number') );
		console.log( index + ": " + $( this ).data('card') );
	});
}

/**
* Check if a move is legal or not.
*/
function checkMove($from, $fromP, $to, $toP){
	let dest_slot = $toP.attr('id');
	console.log('id of destination: '+dest_slot);

	let index = allowed_moving_zones.lastIndexOf(dest_slot);
	if (index == -1) return false;

	if (dest_slot == 'T'){
		let $tcard = $('#T > .card');
		let color_t = $tcard.data('color');
		let number_t = $tcard.data('number');

		console.log('player: '+player+' , pcolor: '+$from.data('color')+ ' - Tcolor: '+color_t+
			' , pnumber: '+  $from.data('number')+ ' - Tnumber: '+number_t );

		if (player == 'CK' && $from.data('color') == color_t) return true;
		else if (player == 'NK' && $from.data('number') == number_t) return true;
		else return false;
	}
	else return true;
}

/**
* Make the current player card slot thicker and colored (red). 
*/
function emphasizeActivePlayer() {
	$('#'+player).css('border', '2px solid red');
}

/**
* Invert the players and reset the previous player card slot with its basic
* color.
*/
function invertPlayers($fromParent) {
	// Invert the players and sets a red border over the current one
	if (player=='CK') {
		player = 'NK';
		$fromParent.css('border', '2px solid #333');
	}
	else {
		player = 'CK';
		$fromParent.css('border', '2px solid #333');
	}
}

/*******************************************************************
* HTML interface functions
*/

/** 
* Called when the PASS button is pressed. Invert the players and regenerate the 
* card draggables.
*/
function passMove(){
	let output_n = $('.card').data('number');
	console.log("Data: ", output_n);

	invertPlayers($('#'+player));
	makeDraggable();
}

/*******************************************************************
* Network functions
*/

/**
* Log into the server. Initialize the connection.
*/
function login() {
	let id = Math.random();
	username = window.prompt("Please, enter your username", 'User_'+String(id).slice(-5));

	if (username == null) username = 'User_'+String(id).slice(-5);

	// socket.emit('login', {'username': username});
}

/**
* Receive the next game hand in json format.
*/
function handleHand() {
	;
}
// graph decompositions, Diestel
// Rasetti
// Knoblock
// abstracting the tower of hanoi
// richard korf, rubik ; 1985