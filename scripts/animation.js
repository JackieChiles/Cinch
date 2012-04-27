//Provides functionality for card movement animations: playing a card from hand
//and clearing the table after each trick.

//Shim layer with setTimeout fallback
window.requestAnimFrame = (function(callback){
  return  window.requestAnimationFrame       || 
          window.webkitRequestAnimationFrame || 
          window.mozRequestAnimationFrame    || 
          window.oRequestAnimationFrame      || 
          window.msRequestAnimationFrame     || 
          function( callback ){
            window.setTimeout(callback, 1000 / 50);
          };
})();

//Globals
var canvas = 0;
var context = 0;
var maxImageDelta = 5; //# of px in each axis image can be away from endPos
var linearDistPerFrame = Math.floor(1.5*maxImageDelta); //px per frame

///////////////////////////
// Card Playing animations
///////////////////////////

function animate(cardObject) {
    cardObject.draw();
    if (cardObject.animateOn) {
        requestAnimFrame( function() {animate(cardObject);});
    }
}

var CardAnimation = function(cardImage, destPlayer) {
    this.cardImage = cardImage;
    
    this.curPos = getStartPosition(destPlayer);
    this.endPos = getEndPosition(destPlayer);
    
    this.animateOn = true;
    
    //Set moveOffest to be used throughout animation
    this.moveOffset = getMoveOffset(this.curPos, this.endPos);

    if (context == 0) { //TODO put this somewhere it won't be called all the time
        canvas = document.getElementById('play-surface');
        context = canvas.getContext('2d');
    }
    
    animate(this);
};

CardAnimation.prototype.draw = function() {  
    // clear -- want only to clear cardImage, leave other things in place
    context.clearRect(this.curPos.x, this.curPos.y, 
                      CinchApp.CARD_IMAGE_WIDTH, CinchApp.CARD_IMAGE_HEIGHT);
                      
    // update -- change the position of cardImage for the next time it is drawn
    //If card is close enough to endPos, move to endPos for final frame
    if ( (Math.abs(this.endPos.x-this.curPos.x) < maxImageDelta) && 
         (Math.abs(this.endPos.y-this.curPos.y) < maxImageDelta) ) { 
        this.curPos.x = this.endPos.x;  this.curPos.y = this.endPos.y;
        this.animateOn = false;
    } else {
    this.curPos.x = this.curPos.x + this.moveOffset.x;
    this.curPos.y = this.curPos.y + this.moveOffset.y;
    }
    
    // draw -- actually render the image
    context.drawImage(this.cardImage, this.curPos.x, this.curPos.y);
};

//Get x, y deltas for each frame; allows for smooth movement in 2 axes
function getMoveOffset(startPos, endPos) {
    var dr, dx, dy; // sides of small triangle
    var R, X, Y; // sides of big triangle
    
    X = endPos.x - startPos.x;
    Y = endPos.y - startPos.y;
    R = Math.sqrt( Math.pow(X, 2) + Math.pow(Y, 2) );
    
    dr = linearDistPerFrame;
    dx = dr / R * X;
    dy = dr / R * Y;  

    return {x: dx, y: dy};
}

//Return starting position of card image (begin animation off of table)
function getStartPosition(player) {
    var x, y;
    
    switch (player) {
      case CinchApp.playerEnum.south:
        x = CinchApp.PLAY_SURFACE_WIDTH / 2 - CinchApp.CARD_IMAGE_WIDTH / 2; 
        y = CinchApp.PLAY_SURFACE_HEIGHT;
        break;
      case CinchApp.playerEnum.west:
        x = 0 - CinchApp.CARD_IMAGE_WIDTH;
        y = CinchApp.PLAY_SURFACE_HEIGHT / 2 - CinchApp.CARD_IMAGE_HEIGHT / 2;
        break;
      case CinchApp.playerEnum.north:
        x = CinchApp.PLAY_SURFACE_WIDTH / 2 - CinchApp.CARD_IMAGE_WIDTH / 2; 
        y = 0 - CinchApp.CARD_IMAGE_HEIGHT;
        break;
      case CinchApp.playerEnum.east:
        x = CinchApp.PLAY_SURFACE_WIDTH + CinchApp.CARD_IMAGE_WIDTH;
        y = CinchApp.PLAY_SURFACE_HEIGHT / 2 - CinchApp.CARD_IMAGE_HEIGHT / 2;
        break;
    }
    return {x: x, y: y};
}

//Return ending position of cards in front of player
function getEndPosition(player) {    
    var x, y;
    
    if (player == CinchApp.playerEnum.south) { //The client
        x = CinchApp.PLAY_SURFACE_WIDTH / 2 - CinchApp.CARD_IMAGE_WIDTH / 2;
        y = CinchApp.PLAY_SURFACE_HEIGHT - CinchApp.CARD_IMAGE_HEIGHT - CinchApp.CARD_EDGE_OFFSET;
    }
    else if (player == CinchApp.playerEnum.west) {
        x = CinchApp.CARD_EDGE_OFFSET;
        y = CinchApp.PLAY_SURFACE_HEIGHT / 2 - CinchApp.CARD_IMAGE_HEIGHT / 2;
    }
    else if (player == CinchApp.playerEnum.north) {
        x = CinchApp.PLAY_SURFACE_WIDTH / 2 - CinchApp.CARD_IMAGE_WIDTH / 2;
        y = CinchApp.CARD_EDGE_OFFSET;
    }
    else { //Should only be CinchApp.playerEnum.east
        x = CinchApp.PLAY_SURFACE_WIDTH - CinchApp.CARD_IMAGE_WIDTH - CinchApp.CARD_EDGE_OFFSET;
        y = CinchApp.PLAY_SURFACE_HEIGHT / 2 - CinchApp.CARD_IMAGE_HEIGHT / 2;
    }
    
    return {x: x, y: y};
}

///////////////////////////
// Board Clearing animations
///////////////////////////

//Wait until all cards are done rendering before proceeding
function finishDrawingCards() {
    //Check each CardAnimation in CinchApp.cardImagesInPlay for animateOn=false.
    if (isAllCardsDoneMoving()) {
        setTimeout( function() {finishClearingBoard();}, 200);
    } else {
        //Wait 200ms and check again
        setTimeout( function(){finishDrawingCards();}, 200);
    }
}

//TODO: lock board while clearing is going on (plays during clearing get cleared)
//TODO: if a play occurs before the client sees the board get cleared, the new play will vanish too
// -- perhaps have everything go into an event queue (would require major overhaul)
function finishClearingBoard() {
    var c;
    var target = getEndPosition(CinchApp.trickWinner); //Move all cards to this position
    
    //Reconfigure cards for new movement
    for (var i = 0; i < CinchApp.cardImagesInPlay.length; i++) {
        c = CinchApp.cardImagesInPlay[i];
        c.animateOn = true;
        c.endPos.x = target.x;  c.endPos.y = target.y;
        c.moveOffset = getMoveOffset(c.curPos, c.endPos);
    }
    CinchApp.cardImagesInPlay[CinchApp.trickWinner].animateOn = false; //Winning card gets special handling
    
    animateBoardClear();
}

function isAllCardsDoneMoving() {
    var cards = CinchApp.cardImagesInPlay;
    var val = 0;
    for (var i = 0; i < cards.length; i++) {
        val = val + (cards[i].animateOn | 0); //val++ for each card still animating
    }
    return (val == 0); //true if no cards animating
}

function animateBoardClear() {
    drawBoardClear();
    if (isAllCardsDoneMoving()) {
        //Prepare card list & table for new trick, after short delay
        setTimeout( function() {
            CinchApp.cardImagesInPlay = [];    
            context.clearRect(0, 0, CinchApp.PLAY_SURFACE_WIDTH, CinchApp.PLAY_SURFACE_HEIGHT);
            viewModel.unlockBoard();
        }, 500);
    } else {
        requestAnimFrame(animateBoardClear);
    }
}

//Draw cards as they are cleared from the board
function drawBoardClear() {
    //Update positions of each card (as needed)
    var c;
    var cards = CinchApp.cardImagesInPlay.filter( function(val) {
                    return val.animateOn; });

    for (var i = 0; i < cards.length; i++) {
        c = cards[i];
        
        //If card is close enough, move to endPos for final frame
        if ( (Math.abs(c.endPos.x-c.curPos.x) < maxImageDelta) && 
             (Math.abs(c.endPos.y-c.curPos.y) < maxImageDelta) ) { 
            c.curPos.x = c.endPos.x;  c.curPos.y = c.endPos.y;
            c.animateOn = false;
        } else { //Set new position
            c.curPos.x = c.curPos.x + c.moveOffset.x;
            c.curPos.y = c.curPos.y + c.moveOffset.y;        
        }
    }
 
    //Clear entire canvas
    context.clearRect(0, 0, CinchApp.PLAY_SURFACE_WIDTH, CinchApp.PLAY_SURFACE_HEIGHT);
     
    //Draw each card -- keep winning card on top of pile by drawing last
    for (var i = 0; i < CinchApp.cardImagesInPlay.length; i++) {
        c = CinchApp.cardImagesInPlay[i]; 
        context.drawImage(c.cardImage, c.curPos.x, c.curPos.y);
    }
    c = CinchApp.cardImagesInPlay[CinchApp.trickWinner];
    context.drawImage(c.cardImage, c.curPos.x, c.curPos.y);
}