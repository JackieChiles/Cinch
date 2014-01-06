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
var linearDistPerFrame = Math.floor(1.2 * maxImageDelta); //px per frame
var movingCards = 0;    //Tracks number of cards in motion for board clearing

///////////////////////////
// Card Playing animations
///////////////////////////

var CardAnimation = function(cardImage, destPlayer) {
    var self = this;

    self.cardImage = cardImage;
    
    self.curPos = getStartPosition(destPlayer);
    self.endPos = getEndPosition(destPlayer);
    
    self.animateOn = true;
    
    //Set moveOffest to be used throughout animation
    self.moveOffset = getMoveOffset(self.curPos, self.endPos);

    if (context == 0) { //TODO put this somewhere it won't be called all the time
        canvas = document.getElementById('play-surface');
        context = canvas.getContext('2d');
    }

    //Functions
    self.draw = function() {
        // clear -- want only to clear cardImage (w/ padding), leave other things in place
        context.clearRect(self.curPos.x - 2, self.curPos.y - 2, 
                          CinchApp.cardImageWidth + 2, CinchApp.cardImageHeight + 2);
                          
        // update -- change the position of cardImage for the next time it is drawn
        //If card is close enough to endPos, move to endPos for final frame
        if ( (Math.abs(self.endPos.x-self.curPos.x) < maxImageDelta) && 
             (Math.abs(self.endPos.y-self.curPos.y) < maxImageDelta) ) { 
            self.curPos.x = self.endPos.x;  self.curPos.y = self.endPos.y;
            self.animateOn = false;
        }
        else {
            self.curPos.x = self.curPos.x + self.moveOffset.x;
            self.curPos.y = self.curPos.y + self.moveOffset.y;
        }
        
        // draw -- actually render the image
        context.drawImage(self.cardImage, self.curPos.x, self.curPos.y);
    };

    self.animate = function() {
        self.draw();

        if (self.animateOn) {
            requestAnimFrame(function() {
                self.animate();
            });
        }
        else { //Animation completed on last draw(); unlock board
            CinchApp.viewModel.unlockBoard();
        }
    };

    //Initialization    
    self.animate();
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
      case CinchApp.players.south:
        x = CinchApp.playSurfaceWidth / 2 - CinchApp.cardImageWidth / 2; 
        y = CinchApp.playSurfaceHeight;
        break;
      case CinchApp.players.west:
        x = 0 - CinchApp.cardImageWidth;
        y = CinchApp.playSurfaceHeight / 2 - CinchApp.cardImageHeight / 2;
        break;
      case CinchApp.players.north:
        x = CinchApp.playSurfaceWidth / 2 - CinchApp.cardImageWidth / 2; 
        y = 0 - CinchApp.cardImageHeight;
        break;
      case CinchApp.players.east:
        x = CinchApp.playSurfaceWidth + CinchApp.cardImageWidth;
        y = CinchApp.playSurfaceHeight / 2 - CinchApp.cardImageHeight / 2;
        break;
    }
    return {x: x, y: y};
}

//Return ending position of cards in front of player
function getEndPosition(player) {    
    var x, y;
    
    if (player == CinchApp.players.south) { //The client
        x = CinchApp.playSurfaceWidth / 2 - CinchApp.cardImageWidth / 2;
        y = CinchApp.playSurfaceHeight - CinchApp.cardImageHeight - CinchApp.cardEdgeOffset;
    }
    else if (player == CinchApp.players.west) {
        x = CinchApp.cardEdgeOffset;
        y = CinchApp.playSurfaceHeight / 2 - CinchApp.cardImageHeight / 2;
    }
    else if (player == CinchApp.players.north) {
        x = CinchApp.playSurfaceWidth / 2 - CinchApp.cardImageWidth / 2;
        y = CinchApp.cardEdgeOffset;
    }
    else { //Should only be CinchApp.players.east
        x = CinchApp.playSurfaceWidth - CinchApp.cardImageWidth - CinchApp.cardEdgeOffset;
        y = CinchApp.playSurfaceHeight / 2 - CinchApp.cardImageHeight / 2;
    }
    
    return {x: x, y: y};
}

///////////////////////////
// Board Clearing animations
///////////////////////////
function finishClearingBoard() {
    var c;
    var target = getEndPosition(CinchApp.viewModel.trickWinner()); //Move all cards to this final position
    var cardImages = CinchApp.viewModel.cardImagesInPlay;

    //Reconfigure cards for new movement
    for (var i = 0; i < cardImages.length; i++) {
        c = cardImages[i];

        if(c) { //Only execute if c is defined
            c.animateOn = true;
            movingCards += 1;
            c.endPos.x = target.x;  c.endPos.y = target.y;
            c.moveOffset = getMoveOffset(c.curPos, c.endPos);
        }
    }

    if(cardImages[CinchApp.viewModel.trickWinner()]) { //Only execute if defined
        cardImages[CinchApp.viewModel.trickWinner()].animateOn = false; //Winning card gets special handling
        movingCards -= 1;
    }
    
    animateBoardClear();
}

function animateBoardClear() {
    drawBoardClear();
    if (movingCards == 0) {
        //Prepare card list & table for new trick, after short delay
        setTimeout( function() {
            CinchApp.viewModel.cardImagesInPlay = [];    
            context.clearRect(0, 0, CinchApp.playSurfaceWidth, CinchApp.playSurfaceHeight);
            CinchApp.viewModel.unlockBoard();
        }, 500);
    }
    else {
        requestAnimFrame(animateBoardClear);
    }
}

//Draw cards as they are cleared from the board
function drawBoardClear() {
    //Update positions of each card (as needed)
    var c;
    var cardImages = CinchApp.viewModel.cardImagesInPlay;
    //Only touch the cards that need animated (i.e. the non-winning cards)
    var cards = cardImages.filter( function(val) {
                    return val.animateOn;
    });

    for (var i = 0; i < cards.length; i++) {
        c = cards[i];
        
        if(c) {
            //If card is close enough, move to endPos for final frame
            if ( (Math.abs(c.endPos.x-c.curPos.x) < maxImageDelta) && 
                 (Math.abs(c.endPos.y-c.curPos.y) < maxImageDelta) ) { 
                c.curPos.x = c.endPos.x;  c.curPos.y = c.endPos.y;
                c.animateOn = false;
                movingCards -= 1;
            } else { //Set new position
                c.curPos.x = c.curPos.x + c.moveOffset.x;
                c.curPos.y = c.curPos.y + c.moveOffset.y;        
            }
        }
    }
 
    //Clear entire canvas
    context.clearRect(0, 0, CinchApp.playSurfaceWidth, CinchApp.playSurfaceHeight);
     
    //Draw each card -- keep winning card on top of pile by drawing last
    for (var i = 0; i < cardImages.length; i++) {
        c = cardImages[i]; 
        c && context.drawImage(c.cardImage, c.curPos.x, c.curPos.y);
    }

    c = cardImages[CinchApp.viewModel.trickWinner()];
    c && context.drawImage(c.cardImage, c.curPos.x, c.curPos.y);
}
