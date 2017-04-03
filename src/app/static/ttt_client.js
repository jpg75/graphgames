/* 
* NOTE: Try to use Knockout.js! 
*/

const cards_colors = {"2H": "red", "3H": "red", "4H": "red",
                    "2C": "black", "3C": "black", "4C": "black"};
const cards_figs = {"2H": "2H.png", "3H": "3H.png", "4H": "4H.png",
                    "2C": "2C.png", "3C": "3C.png", "4C": "4C.png"};
const covered_cards = {"U": false, "C": true, "N": true, 
						"T": false, "CK": false, "NK": false};
const allowed_moving_zones = ["U", "T", "C", "N"];

let card_layout = { 'changed': false, 
					'state' : {'NK': '2C', 'N': '3C', 'U': '4C', 'C': '2H', 'CK': '3H', 'T': '4H', 
							   'GC': '2H', 'PL': 'CK'} };

let player = 'CK', score = 0, goalCard = '2H';
let username = '';
let covered = null;  // whether or not covering cards
let opponent_covered = false;
let replay = false;  // support for replay of game sessions
let multiplayer = false;    // support for multiplayer sessions

/*
* Handlers for network messages over socket-io (websockets)
*/
let socket = io.connect('http://' + document.domain + ':' + location.port);
socket.on('connect', function() {
	console.log('Connected to server @ '+document.domain +':'+location.port);
});
socket.on('hand', handleHand);
socket.on('gameover', function(message) {
    console.log('Game over.');
    if (message['comment']){
        window.alert('Game Over: '+ message['comment']);
    }
	else {
	    window.alert('Game Over: Session ended or timed-out');
	}
});
socket.on('toggle_players', handleTogglePlayers);
socket.on('replay', handleReplay);
socket.on('set_replay', handleSetReplay);


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
			// console.log("Is legal: "+ legal_move);
			let moved_card = $from.data('card');
			
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
				/* Current valid move, sent before inverting players. Currently, the
				 server handles the switching to another user (role).
				*/
				sendMove($toParent.attr('id'), moved_card);

				window.endPos = $to.offset();

				swap($from, $from.offset(), window.endPos, 200);
    	      	swap($to, window.endPos, window.startPos, 500, function() {
        	    	$toParent.html($from.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            		$fromParent.html($to.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            		makeDraggable();
            		// console.log('animation ended!');
          		});

          		score++;
          	}
	    }
	});
	  
	function swap($el, fromPos, toPos, duration, callback) {
		$el.css('position', 'relative')
        	.css(fromPos)
        	.animate(toPos, duration, function() {
            	if (callback) callback();
          	});
	}
});

/**
* Updates the game state bu making every card draggable, but disabled. Then, only the card's
* current player is made enabled and emphasized.
*/
function makeDraggable() {
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

	setCoveredCards();
	eventuallyToggleOpponent();
	initCardsData();
    emphasizeActivePlayer();

	// Set card bindings to flip behavior:
	$('.card').off('dblclick');
	$('.card').dblclick(
					function() {
						console.log('flipping card: '+ $(this).data('card') )
						$(this).find('img').toggle();
					} );
}

/*******************************************************************
* Game related functions
*/

/**
* Generate a sort of metadata inside the card slots
*/ 
function initCardsData(){
	$('.card').each(function(index, el) {
	    let key = $(this).find("[src!='/static/card_back.png']").attr('src').slice(-6, -4);
		$(this).data('color', cards_colors[key] );
		$(this).data('number', key.charAt(0) );
		$(this).data('card', key );
	});

	// set correct card into goal card GUI:
	let gcfile = "/static/" + goalCard + ".png";
	$('#GC').find("img").attr('src', gcfile);
	// UGLY! You can use Knockout.js for example
    $('#info').replaceWith('<div id="info"><h5><p>Number of moves: '+score+"</p><p>Current player turn: " +player+'</p></h5></div>');
}


/**
* Check if a move is legal or not.
*/
function checkMove($from, $fromP, $to, $toP){
	let dest_slot = $toP.attr('id');
	// console.log('id of destination: ' + dest_slot);
 
	let index = allowed_moving_zones.lastIndexOf(dest_slot);
	if (index == -1) return false;

	if (dest_slot == 'T') {
		let $tcard = $('#T > .card');
		let color_t = $tcard.data('color');
		let number_t = $tcard.data('number');

		console.log('player: '+player+' , pcolor: ' + $from.data('color') + ' - Tcolor: '+ color_t +
			' , pnumber: ' + $from.data('number') + ' - Tnumber: ' + number_t );

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
* color. It is just called by a message handler.
*/
function invertPlayers($fromParent) {
	if (player=='CK') {
		player = 'NK';
	}
	else {
		player = 'CK';
	}
}

/**
* Cover the opponent card if the flag is set. The flag is set by the server at every 'hand' message.
*/
function eventuallyToggleOpponent() {
    console.log('eventually toggle: '+player);
	if (player == 'NK') {
		let cardObj = $("#CK").children();
		let viscard = cardObj.find("[src='/static/card_back.png']").css('display');
			
	    console.log('viscard: ' + viscard);
		if (viscard == 'none' && opponent_covered)
			cardObj.find('img').toggle();
		else if (viscard == 'inline' && !opponent_covered)
			cardObj.find('img').toggle();
	}

	if (player == 'CK' && opponent_covered){
		let cardObj = $("#NK").children();
		let viscard = cardObj.find("[src='/static/card_back.png']").css('display');
		
		console.log('viscard: '+viscard);
		if (viscard == 'none' && opponent_covered)
			cardObj.find('img').toggle();
		else if (viscard == 'inline' && !opponent_covered)
			cardObj.find('img').toggle();
	}
}


/**
* Set cards covered according to the server data sent at every hand change.
*/
function setCoveredCards() {
	if (covered !== null) {  
		jQuery.each(covered, function(card, val) { // inspect each card by ID
			$("#" + card).css('border', '2px solid #333');  // resets the card-slot border as unmarked
			if ( (card != 'GC') && (card != 'PL') ) {
				let cardObj = $("#" + card).children();
			 	let visibility = cardObj.find("[src='/static/card_back.png']").css('display');

				if (visibility == 'none' && val) // uncovered amd must be covered
					cardObj.find('img').toggle();
				else if (visibility == 'inline' && !val) // covered and must be uncovered
					cardObj.find('img').toggle(); 
			}
		});
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
    // Send move before inverting players
    sendMove('P', '');
    score++;

	makeDraggable();
}

/*******************************************************************
* Network functions
*/

/**
* Log into the server. Initialize the connection.
*/
function login() {
	// console.log('Username: '+username);
	socket.emit('login', {'username': ''});
}

/**
* Receive the next game hand in json format.
* NOTE: replicated code as in initCardsData() : solve it !
*/
function handleHand(message) {
	console.log('Received HAND: '+ message);

	let cards = message['hand'];
	// collect global data from message:
	covered = message['covered'];
	opponent_covered = message['opponent_covered'];

	console.log('handlehand opponent_covered: ' + opponent_covered);
	console.log(cards);
	console.log(covered);

	if (!replay) {
	    window.alert("New hand");
	}
	$.fx.off = true;  // disable ALL animations
 			
	jQuery.each(cards, function(card, val) {
		console.log(card + ' ' + val);

		if (card == 'GC') {  // set goal card
			goalCard = val;
		}
		else if (card == 'PL') {  // set player turn
		    /* NOTE: ths is the only case (in play mode) in which we call invertPlayers directly
		    since we do not
		    receive a 'toggle_players' message after a move that closes the current hand */
		    if (val != player)
		        invertPlayers($("#" + card));  // NEVER touch player var directly!
		}
		else {
		    // each card is updated with the corresponding figure:
		    $("#" + card).find("[src!='/static/card_back.png']").attr('src', '/static/' + val +'.png');
		}
	});

	makeDraggable();
	// $.fx.off = false;  // enable ALL animations
}


/**
* Handle the 'toggle_players' message and inverts the players. The player turn in managed by the
* server.
*/
function handleTogglePlayers() {
    invertPlayers($('#'+player));
    console.log("Switched to player: "+player);
    makeDraggable();
}

/**
* Enable the replay mode in the client app.
*/
function handleMultiplayer(message) {
    console.log('Multiplayer mode ENABLED');
    multiplayer = true;
    window.alert('Ready for a multiplayer session');

    socket.emit('multiplayer_ready', {}); // notify the server we are ready
}

/**
* Enable the replay mode in the client app.
*/
function handleSetReplay(message) {
    console.log('Replay mode ENABLED');
    replay = true;
    window.alert('Ready to replay session');

    socket.emit('replay_ready', {}); // notify the server we are ready
}

/**
* Handle the reception of 'replay' messages. Each message contains the action to be replayed.
* In case of TTT, an action can be the reception of a new hand or a specific move.
* The message is a json encoded string of the actual action to reproduce.
*/
function handleReplay(message) {
    console.log("HandleREPLAY: " + message);
    // Showing the delay for the next expected move
    $('#replay_delay').replaceWith('<div id="replay_delay"><h5><p>Next move in: ' + message['next_move_at'] + ' seconds</p></h5></div>');

    if (message['hand'] != null) {
        handleHand(message);
    }
    else {
        handleMove(message);
    }
}

/**
* Handle the reproduction of a played move.
*/
function handleMove(message) {
    if (message['move'] == 'P') {  // PASS move
        console.log("Replaying move: " + message['move']);
        score++;
        handleTogglePlayers();
    }
    else {
        console.log("Replaying move: "+message['move']);
        let mv = message['move'];
        // swap the current player card with the one in the position indicated by the move
        // all over the html document
        let pl_card = $('#' + player + ' > .card');
        let move_card = $('#' + mv + ' > .card');
        // card name, es: 2H
        let pl_key = pl_card.find("[src!='/static/card_back.png']").attr('src').slice(-6, -4);
        let move_key = move_card.find("[src!='/static/card_back.png']").attr('src').slice(-6, -4);
        console.log("player card key: "+pl_key);
        console.log("to be moved card key: "+move_key);

        pl_card.find("[src!='/static/card_back.png']").attr('src', '/static/' + move_key + '.png');
        move_card.find("[src!='/static/card_back.png']").attr('src', '/static/' + pl_key + '.png');
        score++;

        handleTogglePlayers();
    }
}

/**
* Send a specific move to the server.
*/
function sendMove(move, moved_card){
	let d = new Date();
	console.log('sending: '+player+ ' move: '+move);
	socket.emit('move', {'username': username, 'player': player, 'move': move, 'ts': 
		d.getUTCFullYear() + '-' + (d.getUTCMonth()+1) + '-' + d.getUTCDate()+ ' ' 
		+ d.getUTCHours() + ':' + d.getUTCMinutes() + ':' + d.getUTCSeconds() + '.' + d.getUTCMilliseconds(), 
		'moved_card': moved_card, 'goal_card': goalCard});
}

