//Provides card movement animations: playing a card from hand and clearing the table after each trick.

CinchApp.animator = {
    positions: [{}, {}, {}, {}],
    cardEdgeOffset: 10,    
    boardClearDelay: 1300,
    playSurfaceWidth: 290,
    playSurfaceHeight: 245,
    cardImageWidth: 72,
    cardImageHeight: 96,
    play: function(imagePath, position) {
        $('<img src="' + imagePath + '" class="card-image" />')
            .css({
                left: CinchApp.animator.positions[position].startX,
                top: CinchApp.animator.positions[position].startY      
            })
            .appendTo('#play-surface')
            .animate({
                left: CinchApp.animator.positions[position].endX,
                top: CinchApp.animator.positions[position].endY
            }, CinchApp.viewModel.unlockBoard);
    },
    boardClear: function(position) {
        var $cardsInPlay = $('#play-surface img');

        $.when($cardsInPlay.animate({
            left: CinchApp.animator.positions[position].endX,
            top: CinchApp.animator.positions[position].endY
        }))
        .then(function() {
            setTimeout(function() {
                $cardsInPlay.remove();
                CinchApp.viewModel.unlockBoard();
            }, 500);
        });
    }
};

//Populate all of the animation start/stop values
(function(a, p, playH, playW, cardH, cardW, edge) {
    //South
    a[p.south].startX = playW / 2 - cardW / 2;
    a[p.south].startY = playH;
    a[p.south].endX = a[p.south].startX;
    a[p.south].endY = a[p.south].startY - cardH - edge;

    //West
    a[p.west].startX = -cardW;
    a[p.west].startY = playH / 2 - cardH / 2;
    a[p.west].endX = a[p.west].startX + cardW + edge;
    a[p.west].endY = a[p.west].startY;

    //North
    a[p.north].startX = a[p.south].startX;
    a[p.north].startY = -cardH;
    a[p.north].endX = a[p.north].startX;
    a[p.north].endY = a[p.north].startY + cardH + edge;

    //East
    a[p.east].startX = playW;
    a[p.east].startY = a[p.west].startY;
    a[p.east].endX = a[p.east].startX - cardW - edge;
    a[p.east].endY = a[p.east].startY;

})(CinchApp.animator.positions,
    CinchApp.players,
    CinchApp.animator.playSurfaceHeight,
    CinchApp.animator.playSurfaceWidth,
    CinchApp.animator.cardImageHeight,
    CinchApp.animator.cardImageWidth,
    CinchApp.animator.cardEdgeOffset);
