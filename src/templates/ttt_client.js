const cards_colors = {"2H": "red", "3H": "red", "4H": "red",
                    "2C": "black", "3C": "black", "4C": "black"};
let player = 'CK';

$(document).ready(function () {
/* initial card positions:
NK    N   UP   C    CK   T	GC	PL
3C   4H   2H   3H   2C   4C	2H	ck
*/
      window.startPos = window.endPos = {};
	  
      init();
      makeDraggable();

      $('.cardSlot').droppable({
        hoverClass: 'hoverClass',
        over: function( event, ui ) {
        	over_what = $(ui.draggable);
        	},

        drop: function(event, ui) {
          var $from = $(ui.draggable),
              $fromParent = $from.parent(),
              $to = $(this).children(),
              $toParent = $(this);

			// Invert the players when an exchange is legal
			if (! $toParent.is($fromParent)) {
		  		if (player=='CK') {
		  			player = 'NK';
          		}
          		else {
          			player = 'CK';
          		}
          		console.log("Are the same!");
		  	}
	
		  console.log('From: ', $from);
		  console.log('To: ', $to);

          window.endPos = $to.offset();

          swap($from, $from.offset(), window.endPos, 200);
          swap($to, window.endPos, window.startPos, 500, function() {
            $toParent.html($from.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            $fromParent.html($to.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            makeDraggable();
          });

	    }
      });

      function makeDraggable() {
		/* let checkedValue = $('.limitDrag').is(":checked");*/
		let checkedValue = document.getElementById("limitDrag").checked;
		console.log(checkedValue); 

		/* $('.card').draggable({ */
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
		
      }

      function swap($el, fromPos, toPos, duration, callback) {
        $el.css('position', 'absolute')
          .css(fromPos)
          .animate(toPos, duration, function() {
            if (callback) callback();
          });
      }
    });

function init(){
    let i = 0;
	
	$('.card').each(function(index, el) {
		$( this ).data('color', 'red');
		console.log( index + ": " + $( this ).data('color') );
		$(this).data('number', $(this).text().charAt(0) );
		console.log( index + ": " + $( this ).data('number') );
		
		console.log( index + ": " + $( this ).text() );
	})
}

/* Called when the PASS button is pressed. */
function passMove(){
	let output_n = $('.card').data('number');
	console.log("Data: ", output_n);
}

