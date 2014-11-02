//Provides card movement animations: playing a card from hand and clearing the table after each trick.

CinchApp.animator = {
    positions: [{}, {}, {}, {}],
    images: [],
    cardEdgeOffset: 10,    
    boardClearDelay: 1300,
    playSurfaceWidth: 290,
    playSurfaceHeight: 245,
    cardImageWidth: 72,
    cardImageHeight: 96,

    //Animates a card played to the position of the given player
    play: function(imagePath, position, doAnimate) {
        var $img = $('<img src="' + imagePath + '" class="card-image" />');

        if(doAnimate) {
            CinchApp.animator.images[position] = $img
            .css({
                left: CinchApp.animator.positions[position].startX,
                top: CinchApp.animator.positions[position].startY
            })
            .appendTo('#play-surface')
            .animate({
                left: CinchApp.animator.positions[position].endX,
                top: CinchApp.animator.positions[position].endY
            }, CinchApp.viewModel.unlockBoard);
        }
        else {
            CinchApp.animator.images[position] = $img
            .appendTo('#play-surface')
            .css({
                left: CinchApp.animator.positions[position].endX,
                top: CinchApp.animator.positions[position].endY
            });

            CinchApp.viewModel.unlockBoard();
        }
    },

    //Animates the clearing of the board at trick's end
    boardClear: function(position, doAnimate) {
        var i = 0;
        var images = CinchApp.animator.images;
        var reset = function() {
            setTimeout(function() {
                CinchApp.animator.boardReset();
                CinchApp.viewModel.unlockBoard();
            }, 500);
        };

        //Always put the winning card on top
        images[position].css('z-index', 50);

        if(doAnimate) {
            for (i = 0; i < images.length; i++) {
                $.when(images[i].animate({
                    left: CinchApp.animator.positions[position].endX,
                    top: CinchApp.animator.positions[position].endY
                }))
                .then(i === images.length -1 ? reset : function() {});
            }
        }
        else {
            for (i = 0; i < images.length; i++) {
                images[i].css({
                    left: CinchApp.animator.positions[position].endX,
                    top: CinchApp.animator.positions[position].endY
                });
            }

            reset();
        }
    },

    //Clears all card images from the board
    boardReset: function() {
        var i = 0;
        var images = CinchApp.animator.images;
        
        for (i = 0; i < images.length; i++) {
            images[i] && CinchApp.animator.images[i].remove();
        }

        CinchApp.animator.images.length = 0;
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
