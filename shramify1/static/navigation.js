/**
 * Simple Back Button Handler
 * Provides reliable back navigation without complex history manipulation
 */

(function() {
  'use strict';

  // Simple back function that uses native browser back
  window.smartBack = function() {
    // Check if there's history to go back to
    if (window.history.length > 1) {
      window.history.back();
    } else {
      // No history, go to home page
      window.location.href = '/';
    }
  };

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      // Ready to handle back button clicks
    });
  }
})();
