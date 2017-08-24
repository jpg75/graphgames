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
let hand_num = 0;
let total_hands_num = 'NA';
let username = '';
let covered = null;  // whether or not covering cards
let card_flip = true;  // whether or not allow flipping cards
let opponent_covered = false;  // force the opponent card always covered
let replay = false;  // support for replay of game sessions
let multiplayer = false;    // support for multi player sessions
/* current player role. used in multi player mode where each client has a fixed player role.
when multiplayer and player_role are different, no card can be operated by the user. */
let player_role = false;
let sid = 0;  // session ID of the current game play. The srv communicates it
let clock = null; // count down clock
let clock_stop = false;  // set when clock is stopped

/*
* Handlers for network messages over socket-io (web-sockets)
*/
let socket = io.connect('http://' + document.domain + ':' + location.port);
socket.on('connect', function() {
	console.log('Connected to server @ '+document.domain +':'+location.port);
});
socket.on('hand', handleHand);
socket.on('gameover', handleGameOver);
socket.on('toggle_players', handleTogglePlayers);
socket.on('replay', handleReplay);
socket.on('set_replay', handleSetReplay);
socket.on('set_multiplayer', handleSetMultiplayer);
socket.on('external_move', handleExternalMove);
socket.on('join', function(message) {
    console.log(message['room']);
    socket.join(message['room']);
    }
);
socket.on('set_player', handleSetPlayer);
socket.on('set_player_role', handleSetPlayerRole);
socket.on('abort_multiplayer', function(message) {
    console.log('Multiplayer aborted.')
    if (message['comment']) {
        $("<p>Multiplayer session aborted: "+ message['comment']+"</p>").alert();
        // window.alert('Multiplayer session aborted: '+ message['comment']);
    }
	else {
	    $("<p>Sorry, multiplayer session failed or timed out: please try again</p>").alert();
	    // window.alert('Sorry, multiplayer session failed or timed out: please try again.');
	}
}
);


// Graph visualization:
let w = 800, h = 480;
let min_zoom = 0.01;
let max_zoom = 100;

// let vis = d3.select("#graph").append("svg").attr("width", w).attr("height", h)
// vis.text("The Graph").select("#graph");

// let sim = d3.forceSimulation();  // setup a force simulation object

//d3.json("/static/games/ttt/data/TTTg.json", function(error, data) {
//    if (error) throw error;
//
//    console.log("Data found: ",data);
//
//    // add "nodes" list to the simulation
//    sim.nodes(data["nodes"]);
//    // add force parameters:
//    sim
//    .force("charge_force", d3.forceManyBody())
//    .force("center_force", d3.forceCenter(w / 2, h / 2));
//
//    // Create the link force
//    // We need the id accessor to use named sources and targets
//    let link_force = d3.forceLink(data["links"])
//                        .id(function(d) { return d.index; });
//    sim.force("links", link_force);
//
//    // prepare the tip
//    let tip = d3.tip()
//        .attr('class', 'd3-tip')
//        .offset([-10, 0])
//        .html(function(d) {
//            return "<strong>Status:</strong> <span style='color:yellow'> CK: " + d.ck + ", C: "
//            + d.dn
//            + ", T: "+ d.target + ", U: " + d.up +", NK: " + d.nk +", N: "+ d.dn+
//            "</span>";
//        })
//
//    let zoom_handler = d3.zoom().scaleExtent([min_zoom, max_zoom]).on("zoom", zoom_actions);
//
//    vis.call(tip);
//    vis.call(zoom_handler);
//
//    /* list of graphical node elements to be attached to the "svg" element. They
//     * corresponds to the view part of the pattern. By having a "g" main container for node and
//     * inks we can easily apply transformations to the whole graph.
//     */
//    let g = vis.append("g").attr("class", "everything");
//
//    /* physically draw links */
//    let link = g.append("g").
//        attr("class", "links")
//        .selectAll("line")
//        .data(data["links"])
//        .enter().append("line")
//        .attr("stroke-width", 2);
//
//    /* physically draw nodes */
//    let node = g.append("g")
//        .attr("class", "nodes")
//        .selectAll("circle")
//        .data(data["nodes"])
//        .enter()
//        .append("circle")
//        .attr("cx", function(d) {return(d.x)})
//        .attr("cy", function(d) {return(d.y)})
//        .attr("r", 10)
//        .attr("fill", "red")
//        .on('mouseover', emphasizeNode)
//        .on('mouseout', deemphasizeNode);
//
//    d3.selectAll('.node').each(function(d) {
//        d.element = this;
//    });
//    sim.on("tick", tickActions);
//
//    let drag_handler = d3.drag().on("start", drag_start).on("drag", drag_drag).on("end", drag_end);
//
//    function drag_start(d) {
//        if (!d3.event.active) sim.alphaTarget(0.05).restart();
//        d.fx = d.x;
//        d.fy = d.y;
//    }
//
//    function drag_drag(d) {
//        d.fx = d3.event.x;
//        d.fy = d3.event.y;
//    }
//
//    function drag_end(d) {
//        if (!d3.event.active) sim.alphaTarget(0);
//        d.fx = d.x;  // makes the node sticky
//        d.fy = d.y;
//    }
//
//    drag_handler(node);
//
//    function tickActions() {
//        // update links:
//        link
//            .attr("x1", function(d) { return d.source.x; })
//            .attr("y1", function(d) { return d.source.y; })
//            .attr("x2", function(d) { return d.target.x; })
//            .attr("y2", function(d) { return d.target.y; });
//
//        //update circle positions to reflect node updates on each tick of the simulation
//        node
//            .attr("cx", function(d) { return d.x; })
//            .attr("cy", function(d) { return d.y; })
//    }
//
//    function zoom_actions(){
//        g.attr("transform", d3.event.transform);
//    }
//
//    function emphasizeNode(d) {
//        tip.show(d);
//        d3.select(this).attr("r", 13).style("fill", "yellow");
//    }
//
//    function deemphasizeNode(d) {
//        tip.hide(d);
//        d3.select(this).attr("r", 10).style("fill", "red");
//    }
//});

$(document).ready(function () {
	/* initial card positions:
	NK    N   UP   C    CK   T	GC	PL
	3C   4H   2H   3H   2C   4C	2H	ck
	*/

	/* count down timer clock */
    clock = $('.clock').FlipClock(1, {
		countdown: true,
		autoStart: false,
		clockFace: 'MinuteCounter',
		callbacks: {
		interval: function() {
		    time = this.factory.getTime().time;
		    console.log("time: " + time );
		    if (time <= 0) {
		        console.log("Expired time!");
                handleGameOver({});
                socket.emit('expired', {});
		    }
        },
        start: function() {
		    console.log("Start triggered: " + this.factory.getTime().time );
      	},
      	stop: function(){
      	    clock_stop = true;
      	}
        },
	});

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
				window.endPos = $to.offset();

				swap($from, $from.offset(), window.endPos, 200);
    	      	swap($to, window.endPos, window.startPos, 500, function() {
        	    	$toParent.html($from.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            		$fromParent.html($to.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            		makeDraggable();
            		// console.log('animation ended!');
          		});
                /* Now the view is consistent with data inside cards objects, we can send the
                move and panel information: */
                sendMove($toParent.attr('id'), moved_card);
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

	/*
	Enable the draggable(s) corresponding to the NK or CK cards.
	when in multi player, no cards are enabled if player differs from player_role.
	*/
	if (player == player_role & multiplayer)  // WARNING: this will screwed up the BOT!!
	    $('#'+player+ '> .card').draggable('enable');

    if (!multiplayer)
        $('#'+player+ '> .card').draggable('enable');

	setCoveredCards();
	eventuallyToggleOpponent();
	initCardsData();
    emphasizeActivePlayer();

	// Set card bindings to flip behavior:
	$('.card').off('dblclick');
	$('.card').off('doubletap');
	$('.card').on({
	        dblclick: function() {
	                    console.log('val: '+ card_flip);
	                    if (card_flip) {
						    console.log('flipping card: '+ $(this).data('card'));
						    $(this).find('img').toggle();
						}
					},
			doubletap:	function() {
						if (card_flip) {
						    console.log('flipping card: '+ $(this).data('card'));
    						$(this).find('img').toggle();
    					}
					}
			});
}

/*******************************************************************
* Game related functions
*/

/**
* Generate a sort of metadata inside the card slots
*/ 
function initCardsData(){
	$('.card').each(function(index, el) {
	    let key = $(this).find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4);
		$(this).data('color', cards_colors[key] );
		$(this).data('number', key.charAt(0) );
		$(this).data('card', key );
	});

	// set correct card into goal card GUI:
	let gcfile = "/static/games/ttt/" + goalCard + ".png";
	$('#GC').find("img").attr('src', gcfile);

    $('#hands span').text(hand_num + '/' + total_hands_num);
	$('#num_moves span').text(score);
	if (player=='CK')
    	$('#player_turn span').text(player + ' (Colore)');
    else
        $('#player_turn span').text(player + ' (Numero)');
	$('#sid span').text(sid);
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
* Invert the players. It is just called by a message handler.
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
    // when multi player, the opponent card must be covered!
    if (multiplayer && player_role=='CK') {
        let cardObj = $("#CK").children();
		let visibility = cardObj.find("[src='/static/games/ttt/card_back.png']").css('display');

        if (visibility == 'inline') { // covered amd must be uncovered
	        cardObj.find('img').toggle();
	    	// console.log("Multiplayer, opponent "+player_role+ "is covered when playing "+player);
	    }

	    cardObj = $("#NK").children();
		visibility = cardObj.find("[src='/static/games/ttt/card_back.png']").css('display');

		if (visibility == 'none') { // uncovered amd must be covered
	        cardObj.find('img').toggle();
	    	// console.log("Multiplayer, opponent "+player_role+ "is covered when playing "+player);
	    }
    }
    else if (multiplayer && player_role=='NK'){
        let cardObj = $("#NK").children();
		let visibility = cardObj.find("[src='/static/games/ttt/card_back.png']").css('display');

        if (visibility == 'inline') { // covered amd must be uncovered
	        cardObj.find('img').toggle();
	    	// console.log("Multiplayer, opponent "+player_role+ "is covered when playing "+player);
	    }

	    cardObj = $("#CK").children();
		visibility = cardObj.find("[src='/static/games/ttt/card_back.png']").css('display');

		if (visibility == 'none') { // uncovered amd must be covered
	        cardObj.find('img').toggle();
	    	// console.log("Multiplayer, opponent "+player_role+ "is covered when playing "+player);
	    }
    }
    else {
	    if (player == 'NK') {
		    let cardObj = $("#CK").children();
		    let viscard = cardObj.find("[src='/static/games/ttt/card_back.png']").css('display');
			
	        console.log('viscard: ' + viscard);
		    if (viscard == 'none' && opponent_covered)
			    cardObj.find('img').toggle();
		    else if (viscard == 'inline' && !opponent_covered)
			    cardObj.find('img').toggle();
	    }

    	if (player == 'CK' && opponent_covered) {
	    	let cardObj = $("#NK").children();
		    let viscard = cardObj.find("[src='/static/games/ttt/card_back.png']").css('display');
		
		    console.log('viscard: '+viscard);
		    if (viscard == 'none' && opponent_covered)
			    cardObj.find('img').toggle();
		    else if (viscard == 'inline' && !opponent_covered)
			    cardObj.find('img').toggle();
	    }
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
		 	    let visibility = cardObj.find("[src='/static/games/ttt/card_back.png']").css('display');

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
* card draggables. It does not work when in multi player and player != player_role.
*/
function passMove() {
    if (clock_stop)
        return;

    time = clock.getTime().time;
    if (time <= 0) return;

    if ((!multiplayer) || (multiplayer & player == player_role)) {
        let output_n = $('.card').data('number');
	    console.log("Data: ", output_n);
        // Send move before inverting players
        sendMove('P', '');
        score++;

    	makeDraggable();
	}
	else console.log('PASS button disabled!');
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
    card_flip = message['card_flip'];
    sid = message['sid'];
    if (message['total_hands_num'])
        total_hands_num = message['total_hands_num'];

    hand_num += 1;  // set the current hand number

	console.log('handlehand opponent_covered: ' + opponent_covered);
	console.log(cards);
	console.log(covered);

	if (!replay) {
        $("<p>New Hand<br>(Nuova Mano)</p>").alert();
        if (clock.getTime().time == 1) {
            clock.setTime(message['timeout']);
        }
        clock.start();
	}
	$.fx.off = true;  // disable ALL animations
 			
	jQuery.each(cards, function(card, val) {
		console.log(card + ' ' + val);

		if (card == 'GC') {  // set goal card
			goalCard = val;
		}
		else if (card == 'PL') {  // set player turn
		    /* NOTE: this is the only case (in play mode) in which we call invertPlayers directly
		    since we do not receive a 'toggle_players' message after a move that
		    closes the current hand. Works only if not in multiplayer mode, where the player is
		    changed by the server. */
		    console.log("multiplayer: "+ multiplayer);
		    if (!multiplayer) {
		        console.log("NOT multiplayer!")
		        if (val != player)
		            invertPlayers($("#" + card));  // NEVER touch player var directly!
		    }
            else { // multi player mode:
                r = 'Color Keeper';
                if (player_role == 'NK'){r = 'Number Keeper';}
                $("#text_message span").text("Your playing role is: " + r );
                console.log("Print player role: " + r);

                console.log("HAND multiplayer, role: " + player_role + " player turn: "+ player +" val: " + val);
                if (player_role == val && val != player) {
                    console.log("Inverting: "+card+ " "+val);
                    invertPlayers($("#" + card));
                }
                if (player_role != val && val != player) {
                    console.log("Inverting: "+card+ " "+val);
                    invertPlayers($("#" + card));
                }
            }
		}
		else {
		    // each card is updated with the corresponding figure:
		    $("#" + card).find("[src!='/static/games/ttt/card_back.png']").attr('src', '/static/games/ttt/' + val +'.png');
		}
	});

	makeDraggable();
	// $.fx.off = false;  // enable ALL animations
}

/**
* Handle an explicit player setting.
*/
function handleSetPlayer(message) {
    console.log("Set to player: " + message['player']);
    // console.log("Set to player role: " + message['player_role']);

    // 1st set normal border to current player, than change it!
    $("#" + player).css('border', '2px solid #333');
    player = message['player'];
    //player_role = message['player_role']
    makeDraggable();
}

/**
* Handle the 'set_player_role' message sent from the server at the beginning of a multi player
game session.
*/
function handleSetPlayerRole(message) {
    console.log("Set to player role: " + message['player_role']);
    player_role = message['player_role'];
}

/**
* Handle the 'toggle_players' message and inverts the players. The player turn in managed by the
* server.
*/
function handleTogglePlayers() {
    invertPlayers($('#'+player));
    console.log("Switched to player: " + player);
    makeDraggable();
}

/**
* Enable the replay mode in the client app.
*/
function handleSetMultiplayer(message) {
    console.log('Multiplayer mode ENABLED');
    multiplayer = true;
    // window.alert('Ready for a multiplayer session');
    $("<p>Ready for a multiplayer session<br>(Pronto per una sessione multi giocatore)</p>").alert();

    socket.emit('multiplayer_ready', {}); // notify the server we are ready
}

/**
* Enable the replay mode in the client app.
*/
function handleSetReplay(message) {
    console.log('Replay mode ENABLED');
    replay = true;
    // window.alert('Ready to replay session');
    $("<p>Ready to replay session</p>").alert();
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
    $('#text_message span').text('Next move in: ' + message['next_move_at'] + ' seconds');

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
    if (message['move']['move'] == 'P') {  // PASS move
        console.log("Replaying move: " + message['move']);
        score++;
        handleTogglePlayers();
    }
    else {
        console.log("Replaying move: " + message['move']);
        let mv = message['move']['move'];
        console.log("mv: " + mv);
        // swap the current player card with the one in the position indicated by the move
        // all over the html document
        let pl_card = $('#' + player + ' > .card');
        let move_card = $('#' + mv + ' > .card');
        // card name, es: 2H
        let pl_key = pl_card.find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4);
        let move_key = move_card.find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4);
        console.log("player card key: "+pl_key);
        console.log("to be moved card key: "+move_key);

        pl_card.find("[src!='/static/games/ttt/card_back.png']").attr('src', '/static/games/ttt/' + move_key + '.png');
        move_card.find("[src!='/static/games/ttt/card_back.png']").attr('src', '/static/games/ttt/' + pl_key + '.png');
        score++;

        handleTogglePlayers();
    }
}

/**
*  Handle the reception of a remote player move (bot or human).
*/
function handleExternalMove(message) {
    console.log("HandleEXTERNALMOVE: " + message);
    if (message['move'] == 'P') {  // PASS move
        score++;
        handleTogglePlayers();
    }
    else {
        let mv = message['move'];
        // swap the current player card with the one in the position indicated by the move
        // all over the html document
        let pl_card = $('#' + player + ' > .card');
        let move_card = $('#' + mv + ' > .card');
        // card name, es: 2H
            let pl_key = pl_card.find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4);
        let move_key = move_card.find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4);
        console.log("player card key: "+pl_key);
        console.log("to be moved card key: "+move_key);

        pl_card.find("[src!='/static/games/ttt/card_back.png']").attr('src', '/static/games/ttt/' + move_key + '.png');
        move_card.find("[src!='/static/games/ttt/card_back.png']").attr('src', '/static/games/ttt/' + pl_key + '.png');
        score++;

        handleTogglePlayers();
    }
}

/**
* Handle the reception of the gameover  messag efrom the server or is called locally by the
* expiring clock.
*/
function handleGameOver(message) {
    console.log('Game over.');
    clock.stop();

    initCardsData();  // updates the score in both multiplayer and solo games
    // disable the chance to move any card
    $('.card').draggable({
    	disabled: true,
    	containment: '#content',
    	zIndex: 99999,
    	revert: 'invalid',
    	start: function(event, ui) {
    		window.startPos = $(this).offset();
    	}
    });

    if (message['comment']) {
        $("<p>Game Over: "+message['comment']+"<br>Gioco Terminato: "+message['comment']+"</p>").alert();
    }
	else {
	    $("<p>Game Over: Session ended or timed-out<br>(Gioco Terminato: Sessione finita o scaduta)</p>").alert();
	}
}

/**
* Send a specific move to the server.
*/
function sendMove(move, moved_card) {
	let d = new Date();
	console.log('sending: '+player+ ' move: '+move);
	socket.emit('move', {
	    'player': player,
	    'move': move,
	    'moved_card': moved_card,
		'goal_card': goalCard,
		'in_hand': $('#' + player + '>.card').find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4),
		'panel': {
		    'CK': $('#CK >.card').find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4),
		    'NK': $('#NK >.card').find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4),
		    'C': $('#C >.card').find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4),
		    'N': $('#N >.card').find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4),
		    'U': $('#U >.card').find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4),
		    'T': $('#T >.card').find("[src!='/static/games/ttt/card_back.png']").attr('src').slice(-6, -4)
		}
	} );
}

/**
* Update the visual graph model according to the move or hand received.
*/
function updateVis(move) {
    ;
}