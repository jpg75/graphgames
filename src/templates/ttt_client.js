cards_colors = {"2H": "red", "3H": "red", "4H": "red",
                    "2C": "black", "3C": "black", "4C": "black"};

$(document).ready(function () {
/* initial card positions:
NK    N   UP   C    CK   T	GC	PL
3C   4H   2H   3H   2C   4C	2H	ck
*/

      window.startPos = window.endPos = {};
	  /* $('<div>' + numbers[i] + '</div>').data( 'number', numbers[i] ).attr( 'id', 'card'+numbers[i] ).appendTo( '#cardPile' )
	*/
      init();
      makeDraggable();

      $('.cardSlot').droppable({
        hoverClass: 'hoverClass',
        drop: function(event, ui) {
          var $from = $(ui.draggable),
              $fromParent = $from.parent(),
              $to = $(this).children(),
              $toParent = $(this);

          window.endPos = $to.offset();

          swap($from, $from.offset(), window.endPos, 200);
          swap($to, window.endPos, window.startPos, 1000, function() {
            $toParent.html($from.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            $fromParent.html($to.css({position: 'relative', left: '', top: '', 'z-index': ''}));
            makeDraggable();
          });
        }
      });

      function makeDraggable() {
		/* var checkedValue = $('.limitDrag').is(":checked");*/
		var checkedValue = document.getElementById("limitDrag").checked;
		console.log(checkedValue); 

        $('.card').draggable({
          containment: '#content',
          zIndex: 99999,
          revert: 'invalid',
          start: function(event, ui) {
            window.startPos = $(this).offset();
          }
        });
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
    var i = 0;
	/* $('.card').data('color', cards_colors.($(this).text()) );*/
	/* $('.card').data('color', 'red' );
	$('.card').data('number', $(this).text() );
	$('.card').data('fig', '');*/
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
	var output_n = $('.card').data('number');
	console.log("Data: ", output_n);
}

