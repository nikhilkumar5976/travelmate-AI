/**
 * TravelMate AI - Core Interactive Engine
 * Handles navigation active state, mobile drawer, explore filters, AI itinerary generator, and auth tabs.
 */

// Global HTML Escaper to prevent ReferenceError and XSS across all modules
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
window.escapeHtml = escapeHtml;
window.escapeReviewText = escapeHtml;
const escapeReviewText = escapeHtml;

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initExploreFilters();
    initAIPlanner();
    initAuthTabs();
    initAIChatbot();
    initReviewSection();
});

/* =========================================
   1. NAVIGATION & MOBILE DRAWER
========================================= */
function initNavigation() {
    // 1. Highlight current active page in navbar
    const currentPath = window.location.pathname.replace(/\/+$/, '') || '/';
    const navLinks = document.querySelectorAll('.nav-links a');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        const normalizedHref = href.replace(/\/+$/, '') || '/';
        
        if (
            normalizedHref === currentPath ||
            (currentPath === '/home' && (normalizedHref === '/home' || normalizedHref === '/index')) ||
            (currentPath === '/' && (normalizedHref === '/' || normalizedHref === '/home'))
        ) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // 1b. Check if user is logged in via Google/Portal
    const savedUser = localStorage.getItem('tm_user');
    const navActions = document.querySelector('.nav-actions');
    if (savedUser && navActions && !document.body.classList.contains('landing-page-mode')) {
        try {
            const user = JSON.parse(savedUser);
            const userHtml = `
                <div class="nav-user-profile">
                    <img src="${user.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80'}" class="nav-user-avatar" alt="${user.name}">
                    <span>${user.name ? user.name.split(' ')[0] : 'Traveler'}</span>
                    <button type="button" class="btn-signout" onclick="signOutUser()">Sign Out</button>
                </div>
            `;
            const loginBtn = navActions.querySelector('.btn-login');
            if (loginBtn) {
                loginBtn.outerHTML = userHtml;
            }
            const greetingPill = document.getElementById('homeGreetingPill');
            if (greetingPill) {
                greetingPill.innerHTML = `<span>👋 Welcome Back, <strong>${user.name}</strong> • AI Concierge Synchronized</span>`;
            }
        } catch (e) {
            console.error(e);
        }
    }

    // 2. Mobile hamburger menu
    const hamburger = document.querySelector('.hamburger');
    const navLinksContainer = document.querySelector('.nav-links');

    if (hamburger && navLinksContainer) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navLinksContainer.classList.toggle('open');
        });

        // Close when clicking outside or clicking any nav link
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navLinksContainer.classList.remove('open');
            });
        });
    }

    // 3. Navbar background tint on scroll
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 40) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }
}

/* =========================================
   2. EXPLORE PAGE FILTERING & SEARCH
========================================= */
function initExploreFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const destinationCards = document.querySelectorAll('.explore-destination-card');
    const searchInput = document.getElementById('exploreSearchInput');
    const sortSelect = document.getElementById('exploreSortSelect');
    const cardGrid = document.querySelector('.explore-card-grid');

    if (!filterButtons.length && !searchInput) return;

    let currentCategory = 'all';
    let searchQuery = '';

    function applyFilters() {
        let visibleCount = 0;

        destinationCards.forEach(card => {
            const cardCategory = (card.getAttribute('data-category') || '').toLowerCase();
            const cardTitle = (card.querySelector('h3')?.textContent || '').toLowerCase();
            const cardDesc = (card.querySelector('p')?.textContent || '').toLowerCase();
            const cardTag = (card.querySelector('.card-badge-category')?.textContent || '').toLowerCase();

            const matchesCategory = (currentCategory === 'all') || (cardCategory === currentCategory);
            const matchesSearch = !searchQuery || 
                cardTitle.includes(searchQuery) || 
                cardDesc.includes(searchQuery) || 
                cardTag.includes(searchQuery);

            if (matchesCategory && matchesSearch) {
                card.style.display = 'flex';
                card.style.animation = 'heroEntrance 0.5s ease forwards';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        // Show/hide empty state message
        let noResultMsg = document.getElementById('noResultsMessage');
        if (!noResultMsg && cardGrid) {
            noResultMsg = document.createElement('div');
            noResultMsg.id = 'noResultsMessage';
            noResultMsg.style.gridColumn = '1 / -1';
            noResultMsg.style.textAlign = 'center';
            noResultMsg.style.padding = '4rem 1rem';
            noResultMsg.style.color = '#94a3b8';
            noResultMsg.innerHTML = `
                <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
                <h3 style="color: #ffffff; margin-bottom: 0.5rem;">No destinations match your criteria</h3>
                <p>Try searching for a different destination or reset the category filter.</p>
            `;
            cardGrid.appendChild(noResultMsg);
        }

        if (noResultMsg) {
            noResultMsg.style.display = visibleCount === 0 ? 'block' : 'none';
        }
    }

    // Category button clicks
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentCategory = (btn.getAttribute('data-filter') || 'all').toLowerCase();
            applyFilters();
        });
    });

    // Search input typing
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.trim().toLowerCase();
            applyFilters();
        });
    }

    // Sorting
    if (sortSelect && cardGrid) {
        sortSelect.addEventListener('change', () => {
            const val = sortSelect.value;
            const cardsArray = Array.from(destinationCards);

            cardsArray.sort((a, b) => {
                const priceA = parseFloat(a.getAttribute('data-price') || '0');
                const priceB = parseFloat(b.getAttribute('data-price') || '0');
                const ratingA = parseFloat(a.getAttribute('data-rating') || '0');
                const ratingB = parseFloat(b.getAttribute('data-rating') || '0');

                if (val === 'price-low') return priceA - priceB;
                if (val === 'price-high') return priceB - priceA;
                if (val === 'rating') return ratingB - ratingA;
                return 0;
            });

            cardsArray.forEach(card => cardGrid.appendChild(card));
        });
    }

    // Parse URL query parameters if present (e.g. ?q=Goa or ?cat=beaches)
    const urlParams = new URLSearchParams(window.location.search);
    const qParam = urlParams.get('q');
    const catParam = urlParams.get('cat');
    if (qParam && searchInput) {
        searchInput.value = qParam;
        searchQuery = qParam.trim().toLowerCase();
    }
    if (catParam) {
        currentCategory = catParam.toLowerCase();
        filterButtons.forEach(btn => {
            if ((btn.getAttribute('data-filter') || '').toLowerCase() === currentCategory) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }
    applyFilters();
}

/* =========================================
   3. AI TRIP PLANNER GENERATOR
========================================= */
window.hasPlanBeenGenerated = false;
let reloadOverlayTimeout = null;
let overlaySafetyTimeout = null;

function showPlannerReloadOverlay(dest, days, style, budget) {
    const overlay = document.getElementById('plannerReloadOverlay');
    if (!overlay) return;
    const titleEl = document.getElementById('reloadTitleDisplay');
    const subtextEl = document.getElementById('reloadSubtextDisplay');
    if (titleEl) {
        titleEl.textContent = `Updating Itinerary for ${dest || 'Destination'}...`;
    }
    if (subtextEl) {
        subtextEl.textContent = `${days} Days • ${style} Archetype • ${budget} Tier`;
    }
    overlay.classList.add('active');

    // Auto-dismiss safety watchdog (guarantees overlay is NEVER stuck)
    if (overlaySafetyTimeout) clearTimeout(overlaySafetyTimeout);
    overlaySafetyTimeout = setTimeout(() => {
        hidePlannerReloadOverlay();
    }, 1200);
}

function hidePlannerReloadOverlay() {
    if (overlaySafetyTimeout) {
        clearTimeout(overlaySafetyTimeout);
        overlaySafetyTimeout = null;
    }
    const overlay = document.getElementById('plannerReloadOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}
window.hidePlannerReloadOverlay = hidePlannerReloadOverlay;

function revealRightTripPlan(dest, days, style, budget) {
    const plannerGrid = document.getElementById('plannerGrid') || document.querySelector('.planner-grid');
    const itineraryOutput = document.getElementById('itineraryOutput');
    const btnText = document.getElementById('btnGeneratePlanText');
    const btnIcon = document.getElementById('btnGeneratePlanIcon');

    window.hasPlanBeenGenerated = true;

    if (plannerGrid) {
        plannerGrid.classList.remove('initial-view');
        plannerGrid.classList.add('has-plan');
    }
    if (itineraryOutput) {
        itineraryOutput.style.display = 'flex';
    }

    if (btnText) btnText.textContent = 'Update Itinerary';
    if (btnIcon) btnIcon.textContent = '✨';

    try {
        if (typeof window.renderDummyItinerary === 'function') {
            window.renderDummyItinerary(dest, days, style, budget);
        }
    } catch (err) {
        console.error('Error rendering trip plan:', err);
    } finally {
        hidePlannerReloadOverlay();
    }

    if (typeof window.syncPlannerCardHeights === 'function') {
        window.syncPlannerCardHeights();
    }

    if (window.innerWidth <= 860 && itineraryOutput) {
        itineraryOutput.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function triggerPlannerParamChange(changedParam, value) {
    const destinationInput = document.getElementById('plannerDestination');
    const durationInput = document.getElementById('plannerDuration');
    const activeStyleCard = document.querySelector('.select-style-card.active');
    const activeBudgetCard = document.querySelector('.select-budget-card.active');

    const dest = destinationInput ? destinationInput.value.trim() : (window.currentItineraryDest || 'Jaipur, Rajasthan');
    const days = durationInput ? parseInt(durationInput.value, 10) : 5;
    const style = activeStyleCard ? (activeStyleCard.getAttribute('data-style') || 'Cultural') : 'Cultural';
    const budget = activeBudgetCard ? (activeBudgetCard.getAttribute('data-budget') || 'Moderate') : 'Moderate';

    // 1. If right page is not yet revealed, reveal it now!
    if (!window.hasPlanBeenGenerated) {
        revealRightTripPlan(dest, days, style, budget);
        showToast(`✨ Trip plan generated for ${dest}!`);
        return;
    }

    // 2. If right page is already showing, perform a sleek "little reload" and show changes!
    if (reloadOverlayTimeout) {
        clearTimeout(reloadOverlayTimeout);
    }

    showPlannerReloadOverlay(dest, days, style, budget);

    const generateBtn = document.getElementById('btnGeneratePlan');
    if (generateBtn) {
        generateBtn.disabled = true;
    }

    reloadOverlayTimeout = setTimeout(() => {
        try {
            if (typeof window.renderDummyItinerary === 'function') {
                window.renderDummyItinerary(dest, days, style, budget);
            }
        } catch (err) {
            console.error('Error updating itinerary:', err);
        } finally {
            hidePlannerReloadOverlay();
            if (generateBtn) {
                generateBtn.disabled = false;
            }
            if (typeof window.syncPlannerCardHeights === 'function') {
                window.syncPlannerCardHeights();
            }
            showToast(`🔄 Updated itinerary for ${dest} (${days} Days, ${style})!`);
        }
    }, 420);
}

window.handlePlannerParamChange = triggerPlannerParamChange;

function initAIPlanner() {
    const form = document.getElementById('aiPlannerForm');
    const destinationInput = document.getElementById('plannerDestination');
    const quickChips = document.querySelectorAll('.chip-tag');
    const styleCards = document.querySelectorAll('.select-style-card');
    const durationInput = document.getElementById('plannerDuration');
    const durationValDisplay = document.getElementById('durationValueDisplay');
    const budgetCards = document.querySelectorAll('.select-budget-card');
    const generateBtn = document.getElementById('btnGeneratePlan');
    const itineraryOutput = document.getElementById('itineraryOutput');

    if (!form || !generateBtn || !itineraryOutput) return;

    // Quick chip click fills destination
    quickChips.forEach(chip => {
        chip.addEventListener('click', () => {
            if (destinationInput) {
                destinationInput.value = chip.textContent.trim().replace('📍 ', '');
                destinationInput.focus();
                triggerPlannerParamChange('destination', destinationInput.value);
            }
        });
    });

    // Travel Style selection
    styleCards.forEach(card => {
        card.addEventListener('click', () => {
            styleCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            const selectedStyle = card.getAttribute('data-style') || 'Cultural';
            triggerPlannerParamChange('style', selectedStyle);
        });
    });

    // Budget tier selection
    budgetCards.forEach(card => {
        card.addEventListener('click', () => {
            budgetCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            const selectedBudget = card.getAttribute('data-budget') || 'Moderate';
            triggerPlannerParamChange('budget', selectedBudget);
        });
    });

    // Duration slider listener
    if (durationInput && durationValDisplay) {
        durationInput.addEventListener('input', () => {
            durationValDisplay.textContent = `${durationInput.value} Days`;
        });
        durationInput.addEventListener('change', () => {
            triggerPlannerParamChange('duration', durationInput.value);
        });
    }

    // Dynamic Fetch function hitting /api/generate-itinerary/ (GET request)
    async function generateItinerary(destination, days) {
        const dest = (destination || '').trim();
        const numDays = Math.max(1, parseInt(days, 10) || 5);

        if (!dest) {
            showToast('⚠️ Please select or enter a target destination.');
            return;
        }

        const activeStyleCard = document.querySelector('.select-style-card.active');
        const effStyle = activeStyleCard ? (activeStyleCard.getAttribute('data-style') || 'Cultural') : 'Cultural';
        const activeBudgetCard = document.querySelector('.select-budget-card.active');
        const effBudget = activeBudgetCard ? (activeBudgetCard.getAttribute('data-budget') || 'Moderate') : 'Moderate';

        if (!window.hasPlanBeenGenerated) {
            revealRightTripPlan(dest, numDays, effStyle, effBudget);
            showToast(`✨ Trip plan generated for ${dest}!`);
        } else {
            triggerPlannerParamChange('submit', null);
        }
    }

    // Expose globally so search/filter can trigger it dynamically
    window.fetchDynamicItinerary = generateItinerary;

    // Form submit listener
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const destination = destinationInput ? destinationInput.value.trim() : '';
        const days = durationInput ? parseInt(durationInput.value, 10) : 5;
        generateItinerary(destination, days);
    });
}

/* =========================================
   SAMPLE & DUMMY ITINERARY PRESETS CATALOG
========================================= */
const SAMPLE_ITINERARY_PRESETS = {
    'jaipur': {
        destination: 'Jaipur, Rajasthan',
        days: 5,
        style: 'Cultural & Heritage',
        budget: 'Moderate',
        cost: '₹37,500',
        daysList: [
            {
                day: 1,
                theme: 'Royal Bastions & Heritage Flavors',
                slots: [
                    { time: '08:30 AM', activity: 'Artisanal breakfast with spicy Pyaaz Kachori and saffron masala chai at the iconic Rawat Mishthan Bhandar.' },
                    { time: '10:30 AM', activity: 'Ascend to Amber Fort, marveling at the mirror mosaics of Sheesh Mahal and grand Rajput ramparts.' },
                    { time: '02:00 PM', activity: 'Royal heritage Rajasthani Thali lunch at 1135 AD with panoramic desert fort vistas.' },
                    { time: '06:30 PM', activity: 'Sunset golden hour photography at Jal Mahal water palace and evening gem shopping at Johari Bazaar.' }
                ]
            },
            {
                day: 2,
                theme: 'Pink City Iconography & Astronomy',
                slots: [
                    { time: '09:00 AM', activity: 'Iconic honeycomb facade photography at Hawa Mahal followed by morning espresso at Wind View Cafe.' },
                    { time: '11:30 AM', activity: 'Guided exploration of City Palace royal museum & UNESCO-listed Jantar Mantar astronomical observatory.' },
                    { time: '02:30 PM', activity: 'Traditional Rajasthani feast at Handi Restaurant on MI Road trying authentic Laal Maas and Bajra roti.' },
                    { time: '06:00 PM', activity: 'Golden sunset vista overlooking the entire Pink City skyline from the mountain ramparts of Nahargarh Fort.' }
                ]
            },
            {
                day: 3,
                theme: 'Stepwells, Cannons & Artisan Villages',
                slots: [
                    { time: '08:30 AM', activity: 'Early morning photography at the symmetrical geometric stepwell of Panna Meena Ka Kund.' },
                    { time: '11:00 AM', activity: 'Jaigarh Fort visit to marvel at Jaivana, the world\'s largest cannon on wheels, and secret underground passages.' },
                    { time: '02:00 PM', activity: 'Traditional wooden block-printing workshop & blue pottery shopping in Sanganer craft village.' },
                    { time: '07:00 PM', activity: 'Immersive cultural folk dance, puppet show, and royal village dining feast under desert tents at Chokhi Dhani.' }
                ]
            },
            {
                day: 4,
                theme: 'Palace Gardens & High-Tea Culture',
                slots: [
                    { time: '09:00 AM', activity: 'Peaceful stroll through lush terraced fountains and painted pavilions of Sisodia Rani Ka Bagh.' },
                    { time: '11:30 AM', activity: 'Explore Albert Hall Museum, admiring centuries-old Rajput armor, miniatures, and Persian carpets.' },
                    { time: '02:30 PM', activity: 'Modern fusion brunch and chai degustation at Tapri Central overlooking Central Park.' },
                    { time: '06:30 PM', activity: 'Evening sound-and-light spectacle at Amber Fort under the starry Aravalli night sky.' }
                ]
            },
            {
                day: 5,
                theme: 'Spiritual Sanctuaries & Sunset Bazaars',
                slots: [
                    { time: '08:30 AM', activity: 'Serene morning prayers and white marble carvings at Birla Mandir (Laxmi Narayan Temple).' },
                    { time: '11:00 AM', activity: 'Adventure hike through the mountain gorge to sacred Galta Ji (Monkey Temple) natural freshwater springs.' },
                    { time: '02:00 PM', activity: 'Rooftop leisure lunch at Baradari Restaurant inside City Palace grounds.' },
                    { time: '05:30 PM', activity: 'Souvenir treasure hunt in Bapu Bazaar for handcrafted Mojaris, camel leather goods, and bandhani textiles.' }
                ]
            }
        ]
    },
    'goa': {
        destination: 'Goa Coastline',
        days: 4,
        style: 'Coastal & Relaxed',
        budget: 'Moderate',
        cost: '₹30,000',
        daysList: [
            {
                day: 1,
                theme: 'Portuguese Heritage & Sunset Bastions',
                slots: [
                    { time: '08:30 AM', activity: 'Wood-fired croissants, eggs benedict, and artisanal cold brew at Baba Au Rhum in Anjuna.' },
                    { time: '11:00 AM', activity: 'Explore the 17th-century Portuguese defense bastion and lighthouse at Fort Aguada.' },
                    { time: '02:00 PM', activity: 'Authentic Goan Fish Curry Thali lunch at Ritz Classic in Panaji.' },
                    { time: '04:30 PM', activity: 'Heritage walking tour amidst vibrant colonial Portuguese villas of Fontainhas Latin Quarter.' },
                    { time: '07:00 PM', activity: 'Sunset cocktails and clifftop Greek dining with live fire acrobats at Thalassa in Siolim.' }
                ]
            },
            {
                day: 2,
                theme: 'Old Goa Cathedrals & Spice Plantations',
                slots: [
                    { time: '09:00 AM', activity: 'Artisan smoothie bowls and coffee at Cafe Bodega inside Sunaparanta Arts Centre.' },
                    { time: '11:30 AM', activity: 'Marvel at UNESCO World Heritage Basilica of Bom Jesus and Se Cathedral in historic Old Goa.' },
                    { time: '02:00 PM', activity: 'Guided spice plantation walk and banana-leaf Goan buffet at Sahakari Spice Farm in Ponda.' },
                    { time: '06:00 PM', activity: 'Luxury sunset cruise on Mandovi River with traditional Goan folk performances and dolphin sightings.' }
                ]
            },
            {
                day: 3,
                theme: 'Pristine South Bays & Secluded Cliffs',
                slots: [
                    { time: '08:30 AM', activity: 'Organic granola and cold-pressed juices at The Space Goa in Canacona.' },
                    { time: '11:00 AM', activity: 'Kayaking along the crescent shoreline of Palolem Beach and boat safari to secluded Butterfly Beach.' },
                    { time: '02:00 PM', activity: 'Riverside butter garlic tiger prawns and crab masala feast at Fisherman\'s Wharf in Cavelossim.' },
                    { time: '06:00 PM', activity: 'Spectacular sunset views from the dramatic cliff ruins of Cabo de Rama Fort overlooking the Arabian Sea.' }
                ]
            },
            {
                day: 4,
                theme: 'Bohemian Flea Bazaars & Coastal Farewell',
                slots: [
                    { time: '09:30 AM', activity: 'French crepes and ocean-facing shakshuka at Eva Cafe perched above Anjuna cliffs.' },
                    { time: '12:00 PM', activity: 'Boutique treasure hunting at Anjuna Flea Market for brass handicrafts and linen resort-wear.' },
                    { time: '03:00 PM', activity: 'Sun lounger relaxation with fresh coconuts along peaceful Ashvem Beach.' },
                    { time: '07:30 PM', activity: 'Farm-to-table Goan fusion dinner at The Black Sheep Bistro in Panaji.' }
                ]
            }
        ]
    },
    'manali': {
        destination: 'Manali & Rohtang Pass, Himachal',
        days: 5,
        style: 'Alpine Thrills & Mountains',
        budget: 'Moderate',
        cost: '₹37,500',
        daysList: [
            {
                day: 1,
                theme: 'Cedar Forests & Old Manali Vibe',
                slots: [
                    { time: '08:30 AM', activity: 'Apple crumble pie and freshly brewed mountain espresso at Dylan\'s Toasted & Roasted Cafe.' },
                    { time: '10:30 AM', activity: 'Walk through towering Deodar cedar groves to the 16th-century wooden pagoda Hadimba Temple.' },
                    { time: '02:00 PM', activity: 'Wood-fired trout and pizza at Cafe 1947 right beside the rushing Manalsu River.' },
                    { time: '06:00 PM', activity: 'Evening shopping on Mall Road for handcrafted Kullu shawls, prayer wheels, and apricot oil.' }
                ]
            },
            {
                day: 2,
                theme: 'Solang Valley Adventure & Hot Springs',
                slots: [
                    { time: '08:00 AM', activity: 'Aloo paratha breakfast with homemade mountain butter at Drifters\' Cafe.' },
                    { time: '10:00 AM', activity: 'Paragliding, quad biking, and scenic gondola ropeway ride across Solang Valley.' },
                    { time: '02:00 PM', activity: 'Hot Tibetan Thukpa and steamed momos at Chopsticks Restaurant.' },
                    { time: '05:00 PM', activity: 'Rejuvenate in natural geothermal sulfur springs at ancient Vashisht Temple village.' }
                ]
            },
            {
                day: 3,
                theme: 'Rohtang Pass & Atal Tunnel Marvel',
                slots: [
                    { time: '07:00 AM', activity: 'Early morning mountain drive across winding Himalayan hairpins to Rohtang Pass (13,058 ft).' },
                    { time: '10:30 AM', activity: 'Spectacular panoramic vistas of glaciers, snow walls, and Pir Panjal mountain ranges.' },
                    { time: '02:00 PM', activity: 'Steaming Maggi and Masala Chai at high-altitude mountain stalls.' },
                    { time: '05:30 PM', activity: 'Return drive through the engineering triumph of Atal Tunnel (9.02 km) beneath Rohtang.' }
                ]
            },
            {
                day: 4,
                theme: 'Heritage Castles & Roerich Art in Naggar',
                slots: [
                    { time: '09:00 AM', activity: 'Scenic drive down the Beas Valley to medieval timber-and-stone Naggar Castle.' },
                    { time: '11:30 AM', activity: 'Visit the Nicholas Roerich Art Gallery and Estate showcasing mystical Himalayan canvases.' },
                    { time: '02:00 PM', activity: 'Fresh grilled trout lunch at Naggar Castle rooftop cafe overlooking apple orchards.' },
                    { time: '06:00 PM', activity: 'Craft mountain cider tasting and acoustic live folk music in Old Manali.' }
                ]
            },
            {
                day: 5,
                theme: 'Waterfall Treks & Riverside Solitude',
                slots: [
                    { time: '08:30 AM', activity: 'Fluffy pancake breakfast at Rocky\'s Cafe with 360-degree snow peak views.' },
                    { time: '10:30 AM', activity: 'Pine forest trek to the cascading Jogini Waterfalls with pristine natural plunge pools.' },
                    { time: '02:00 PM', activity: 'Farewell feast with wood-fired sourdough sandwiches at The Johnson\'s Cafe.' },
                    { time: '05:00 PM', activity: 'Collect jars of organic forest honey and handwoven pashminas before departure.' }
                ]
            }
        ]
    },
    'kerala': {
        destination: 'Munnar & Kerala Backwaters',
        days: 5,
        style: 'Lush Mist & Serene Waters',
        budget: 'Luxury',
        cost: '₹80,000',
        daysList: [
            {
                day: 1,
                theme: 'Rolling Tea Estates & Mountain Mist',
                slots: [
                    { time: '08:30 AM', activity: 'Traditional soft Appams with vegetable stew and filter coffee at Saravana Bhavan Munnar.' },
                    { time: '10:30 AM', activity: 'Guided tea processing tour at KDHP Tea Museum and scenic photography at Mattupetty Dam.' },
                    { time: '02:00 PM', activity: 'Kerala spiced curry lunch at Rapsy Restaurant followed by Echo Point speedboating.' },
                    { time: '06:00 PM', activity: 'Panoramic sunset view over the Western Ghats from Top Station (5,600 ft) amidst rolling clouds.' }
                ]
            },
            {
                day: 2,
                theme: 'Eravikulam Wildlife & Spice Gardens',
                slots: [
                    { time: '08:00 AM', activity: 'Morning safari through Eravikulam National Park spotting endangered Nilgiri Tahr mountain goats.' },
                    { time: '12:00 PM', activity: 'Guided spice plantation walk in Anachal discovering cardamom, cinnamon, and vanilla vines.' },
                    { time: '02:30 PM', activity: 'Authentic 24-dish Kerala Sadhya banquet served on banana leaves.' },
                    { time: '06:00 PM', activity: 'Mesmerizing Kathakali dance and Kalaripayattu martial arts show at Punarjani Traditional Village.' }
                ]
            },
            {
                day: 3,
                theme: 'Alleppey Luxury Houseboat Cruise',
                slots: [
                    { time: '08:00 AM', activity: 'Scenic descent from the mist-covered mountains through rubber plantations to Alleppey backwaters.' },
                    { time: '12:30 PM', activity: 'Check-in aboard a private luxury thatched Kettuvallam (Houseboat) at Punnamada Jetty.' },
                    { time: '01:30 PM', activity: 'Onboard fresh lunch featuring Karimeen Pollichathu (Pearl Spot fish wrapped in banana leaf).' },
                    { time: '05:30 PM', activity: 'Serene sunset cruise through Vembanad Lake watching village life and swaying coconut palms.' }
                ]
            },
            {
                day: 4,
                theme: 'Village Canoes & Arabian Sea Sands',
                slots: [
                    { time: '08:00 AM', activity: 'Sunrise narrow-canal canoe ride through village waterways with fresh sweet coconut water.' },
                    { time: '11:30 AM', activity: 'Stroll along peaceful Marari Beach, known for pristine white sands and traditional fishing catamarans.' },
                    { time: '02:30 PM', activity: 'Coastal seafood lunch at Marari Beach Resort featuring fresh catch of the day.' },
                    { time: '06:00 PM', activity: 'Evening sunset stroll along the historic 150-year-old Alappuzha Beach Pier.' }
                ]
            },
            {
                day: 5,
                theme: 'Fort Kochi Heritage & Art Cafes',
                slots: [
                    { time: '09:00 AM', activity: 'Drive to Fort Kochi to photograph the iconic cantilevered Chinese Fishing Nets at harbor entrance.' },
                    { time: '11:30 AM', activity: 'Historical walk through St. Francis Church (Vasco da Gama\'s tomb) and Jew Town spice bazaar.' },
                    { time: '02:00 PM', activity: 'Cold brew and artisanal brunch at Kashi Art Cafe surrounded by contemporary installations.' },
                    { time: '05:30 PM', activity: 'Antiques and heirloom spice shopping along the quaint cobblestone lanes of Mattancherry.' }
                ]
            }
        ]
    },
    'ladakh': {
        destination: 'Leh Ladakh Frontier, Ladakh',
        days: 6,
        style: 'High Pass Expedition & Monasteries',
        budget: 'Luxury',
        cost: '₹96,000',
        daysList: [
            {
                day: 1,
                theme: 'Acclimatization, Leh Palace & Shanti Stupa',
                slots: [
                    { time: '09:00 AM', activity: 'Gentle morning acclimatization with warm Butter Tea and Ladakhi Tingmo bread in Leh.' },
                    { time: '01:00 PM', activity: 'Wholesome organic Thukpa and momo lunch at Gesmo Restaurant in Leh Main Bazaar.' },
                    { time: '04:30 PM', activity: 'Spin prayer wheels at Shanti Stupa enjoying a golden hour panoramic view of Stok Kangri range.' },
                    { time: '07:30 PM', activity: 'Traditional Ladakhi mutton stew dinner (Chhutagi) at The Tibetan Kitchen.' }
                ]
            },
            {
                day: 2,
                theme: 'Thiksey Gompa & Indus Valley Monasteries',
                slots: [
                    { time: '08:30 AM', activity: 'Witness the morning monks\' chanting ceremony at Thiksey Monastery (mini Potala Palace).' },
                    { time: '11:30 AM', activity: 'Explore Hemis Monastery, the wealthiest Buddhist gompa nestled in a hidden mountain gorge.' },
                    { time: '02:30 PM', activity: 'Rooftop lunch at Cafe Cloud in Shey surrounded by willow and poplar trees.' },
                    { time: '05:00 PM', activity: 'Hall of Fame military memorial honoring valiant guardians of the high Himalayas.' }
                ]
            },
            {
                day: 3,
                theme: 'Khardung La Pass & Nubra Desert Dunes',
                slots: [
                    { time: '07:30 AM', activity: 'Ascend the legendary Khardung La Pass (17,982 ft), one of the world\'s highest motorable passes.' },
                    { time: '12:00 PM', activity: 'Descend into lush Nubra Valley and check into luxury glamping dome tents in Hunder.' },
                    { time: '04:30 PM', activity: 'Ride double-humped Bactrian Camels across the surreal white sand dunes of Hunder at golden hour.' },
                    { time: '07:30 PM', activity: 'Stargazing under the crystal-clear Milky Way galaxy with zero light pollution.' }
                ]
            },
            {
                day: 4,
                theme: 'Diskit Colossus & Azure Pangong Tso',
                slots: [
                    { time: '08:30 AM', activity: 'Marvel at the 106-ft outdoor statue of Maitreya Buddha at Diskit Monastery overlooking the valley.' },
                    { time: '11:00 AM', activity: 'Rugged off-road expedition along the turquoise Shyok River towards Pangong Lake.' },
                    { time: '03:00 PM', activity: 'Witness the color-shifting azure and turquoise waters of Pangong Tso (14,270 ft).' },
                    { time: '06:30 PM', activity: 'Sunset photography at the famous lakeside promontory followed by cozy tent dining.' }
                ]
            },
            {
                day: 5,
                theme: 'Chang La Pass & Return to Leh',
                slots: [
                    { time: '07:00 AM', activity: 'Magical sunrise over the crystalline lake with rare migratory bar-headed geese.' },
                    { time: '10:30 AM', activity: 'Cross snow-covered Chang La Pass (17,688 ft) stopping for warm tea at the army outpost.' },
                    { time: '02:30 PM', activity: 'Late lunch and wood-fired pizza at Bon Appetit with views of Leh valley.' },
                    { time: '06:00 PM', activity: 'Souvenir shopping in Leh for authentic certified Pashmina shawls, dried apricots, and turquoise gems.' }
                ]
            },
            {
                day: 6,
                theme: 'Magnetic Hill & River Confluence',
                slots: [
                    { time: '09:00 AM', activity: 'Drive down the Leh-Srinagar highway to experience the gravity-defying Magnetic Hill.' },
                    { time: '11:00 AM', activity: 'Gaze at the dramatic confluence of the emerald Indus and muddy Zanskar rivers at Nimmu.' },
                    { time: '02:00 PM', activity: 'Grand farewell feast at Alchi Kitchen sampling artisanal apricot dessert and Khambir.' }
                ]
            }
        ]
    },
    'varanasi': {
        destination: 'Varanasi Ghats, Uttar Pradesh',
        days: 5,
        style: 'Spiritual & Cultural',
        budget: 'Moderate',
        cost: '₹37,500',
        daysList: [
            {
                day: 1,
                theme: 'Sacred Dawn, Ganges Rowboat & Subah-e-Banaras',
                slots: [
                    { time: '05:30 AM', activity: 'Sunrise wooden rowboat cruise along ancient stone ghats from Assi Ghat to Manikarnika Ghat.' },
                    { time: '08:00 AM', activity: 'Crispy Kachori Sabzi and piping hot Jalebi breakfast at Ram Bhandar in Thatheri Bazaar.' },
                    { time: '10:30 AM', activity: 'Sacred darshan at the holy golden spire Kashi Vishwanath Temple via the river corridor.' },
                    { time: '06:00 PM', activity: 'Mesmerizing evening Maha Aarti ceremony at Dashashwamedh Ghat with chanting and brass lamps.' }
                ]
            },
            {
                day: 2,
                theme: 'Buddhist Cradle of Sarnath & Weaver Quarters',
                slots: [
                    { time: '08:30 AM', activity: 'Visit sacred Sarnath where Buddha gave his first sermon; explore Dhamek Stupa & Ashoka Pillar.' },
                    { time: '12:30 PM', activity: 'Traditional Banarasi Thali lunch followed by rich saffron Malaiyo dessert at Chowk.' },
                    { time: '03:30 PM', activity: 'Explore century-old Banarasi silk handloom weaving workshops in Madanpura.' },
                    { time: '06:30 PM', activity: 'Evening boat ride watching illuminated ghat reflections and tasting authentic Banarasi Paan.' }
                ]
            },
            {
                day: 3,
                theme: 'Havelis, Akhadas & Riverfront Meditation',
                slots: [
                    { time: '06:00 AM', activity: 'Witness traditional mud wrestling (Kushti) workouts at Tulsi Ghat Akhada at dawn.' },
                    { time: '09:00 AM', activity: 'Thick creamy pomegranate and saffron lassi at the world-famous Blue Lassi shop.' },
                    { time: '11:30 AM', activity: 'Heritage walk exploring the ancient stepped architecture of Man Mandir Ghat observatory.' },
                    { time: '05:30 PM', activity: 'Peaceful sunset flute recital and classical sitar session overlooking the river at Assi Ghat.' }
                ]
            },
            {
                day: 4,
                theme: 'University Heritage & Authentic Baati Chokha',
                slots: [
                    { time: '09:00 AM', activity: 'Explore lush green campus of Banaras Hindu University and New Vishwanath Temple.' },
                    { time: '12:00 PM', activity: 'Admire miniature paintings and sculptures at Bharat Kala Bhavan museum.' },
                    { time: '02:30 PM', activity: 'Authentic rustic Dal Baati Chokha feast at Baati Chokha restaurant in Teliyabag.' },
                    { time: '06:30 PM', activity: 'Evening quiet boat ride past Harishchandra Ghat listening to temple bells.' }
                ]
            },
            {
                day: 5,
                theme: 'Sacred Ghats Farewell & Heritage Bazaars',
                slots: [
                    { time: '08:30 AM', activity: 'Morning yoga and meditation session along peaceful Prabhu Ghat.' },
                    { time: '11:00 AM', activity: 'Souvenir treasure hunt in Vishwanath Gali for brass idols, rudraksha, and wooden toys.' },
                    { time: '02:00 PM', activity: 'Tamatar Chaat and Palak Chaat tasting at Kashi Chat Bhandar in Godowlia.' },
                    { time: '06:00 PM', activity: 'Farewell sunset boat cruise from Rajghat to Assi with illuminated evening skyline.' }
                ]
            }
        ]
    },
    'udaipur': {
        destination: 'Udaipur (City of Lakes), Rajasthan',
        days: 5,
        style: 'Royal & Romantic',
        budget: 'Moderate',
        cost: '₹37,500',
        daysList: [
            {
                day: 1,
                theme: 'City of Lakes, Royal Palaces & Pichola Boat Ride',
                slots: [
                    { time: '08:30 AM', activity: 'Lakeview breakfast of Poha and masala chai at Jheel\'s Ginger Coffee Bar on Gangaur Ghat.' },
                    { time: '10:00 AM', activity: 'Extensive guided tour through colossal courtyards and mirror galleries of City Palace.' },
                    { time: '02:00 PM', activity: 'Traditional Rajasthani lunch at Ambrai Restaurant with breathtaking panoramas across Lake Pichola.' },
                    { time: '05:30 PM', activity: 'Sunset boat cruise around the marble island palace of Jag Mandir with golden Aravalli hill views.' }
                ]
            },
            {
                day: 2,
                theme: 'Monsoon Fortresses & Heritage Folk Dances',
                slots: [
                    { time: '09:00 AM', activity: 'Ascend the winding hill road to Sajjangarh (Monsoon Palace) perched 3,100 ft above the valley.' },
                    { time: '12:00 PM', activity: 'Stroll through marble elephant fountains and lotus pools of Saheliyon Ki Bari.' },
                    { time: '03:00 PM', activity: 'Artisanal miniature painting shopping and pottery browsing in the Old City lanes.' },
                    { time: '07:00 PM', activity: 'Captivating Dharohar Rajasthani folk dance, fire show, and puppet performance at Bagore Ki Haveli.' }
                ]
            },
            {
                day: 3,
                theme: 'Lake Fateh Sagar & Royal Cenotaphs',
                slots: [
                    { time: '08:30 AM', activity: 'Morning walking loop and fresh cold coffee along the lakeside promenade of Fateh Sagar.' },
                    { time: '11:00 AM', activity: 'Explore the grand carved marble cenotaphs of Mewar kings at historic Ahar Cenotaphs.' },
                    { time: '02:00 PM', activity: 'Mewari royal dining feast at 1559 AD surrounded by heritage botanical gardens.' },
                    { time: '06:00 PM', activity: 'Cable car ropeway ride up to Karni Mata temple for sunset city vistas.' }
                ]
            },
            {
                day: 4,
                theme: 'Great Wall of India & Marble Temples',
                slots: [
                    { time: '08:00 AM', activity: 'Scenic day expedition to colossal Kumbhalgarh Fort with its 36-km Great Wall of India ramparts.' },
                    { time: '01:00 PM', activity: 'Marwari thali lunch overlooking the fortress battlements.' },
                    { time: '03:30 PM', activity: 'Visit Ranakpur Jain Temple marveling at 1,444 uniquely hand-carved marble pillars.' },
                    { time: '07:30 PM', activity: 'Return drive through scenic Aravalli mountain passes to Udaipur.' }
                ]
            },
            {
                day: 5,
                theme: 'Artisan Crafts & Sunset Farewell',
                slots: [
                    { time: '09:00 AM', activity: 'Explore Shilpgram rural arts and crafts village complex watching folk artisans at work.' },
                    { time: '12:00 PM', activity: 'Visit historic 1651 Jagdish Temple admiring intricate carved stone pillars.' },
                    { time: '02:30 PM', activity: 'Leisurely brunch at Grasswood Cafe with organic juices and sandwiches.' },
                    { time: '06:30 PM', activity: 'Farewell candlelight dinner at Tribute restaurant by the waters of Lake Rang Sagar.' }
                ]
            }
        ]
    },
    'srinagar': {
        destination: 'Srinagar & Dal Lake, Kashmir',
        days: 5,
        style: 'Scenic & Romantic',
        budget: 'Moderate',
        cost: '₹37,500',
        daysList: [
            {
                day: 1,
                theme: 'Dal Lake Shikara & Floating Bazaars',
                slots: [
                    { time: '06:00 AM', activity: 'Sunrise Shikara boat ride on Dal Lake passing floating lotus beds and morning vegetable market.' },
                    { time: '09:00 AM', activity: 'Traditional Noon Chai and hot Kashmiri Girda bread at Ahdoos on the Jhelum riverbank.' },
                    { time: '11:30 AM', activity: 'Ascend Shankaracharya Hill to 8th-century stone temple for 360-degree valley panoramas.' },
                    { time: '06:30 PM', activity: 'Sunset over the lake from carved cedar wood deck of your luxury heritage houseboat.' }
                ]
            },
            {
                day: 2,
                theme: 'Imperial Mughal Terraces & Hazratbal',
                slots: [
                    { time: '09:00 AM', activity: 'Walk terraced waterfalls and chinar tree avenues of Nishat Bagh & Shalimar Bagh.' },
                    { time: '01:00 PM', activity: 'Authentic 7-course Kashmiri Wazwan feast featuring Rogan Josh and Gushtaba at Mughal Darbar.' },
                    { time: '04:00 PM', activity: 'Peaceful lakeside prayer and white marble architecture at historic Hazratbal Shrine.' },
                    { time: '06:30 PM', activity: 'Evening drive along Boulevard Road sampling roasted spiced corn and Kashmiri Kahwa.' }
                ]
            },
            {
                day: 3,
                theme: 'Old City Wooden Bridges & Pashmina Masters',
                slots: [
                    { time: '09:30 AM', activity: 'Heritage walk through Old Srinagar crossing wooden Zaina Kadal bridges and Jamia Masjid.' },
                    { time: '01:00 PM', activity: 'Traditional Tujji barbecue skewers at Khayam Chowk.' },
                    { time: '03:30 PM', activity: 'Visit master artisan ateliers for hand-spun Pashmina shawls and walnut wood carvings.' },
                    { time: '06:00 PM', activity: 'Chashme Shahi natural royal spring gardens overlooking Zabarwan mountain range.' }
                ]
            },
            {
                day: 4,
                theme: 'Meadow of Flowers Excursion (Gulmarg)',
                slots: [
                    { time: '07:30 AM', activity: 'Scenic mountain drive to Gulmarg (Meadow of Flowers) surrounded by pine peaks.' },
                    { time: '10:30 AM', activity: 'Ride the world\'s highest Gondola cable car to Phase 2 Kongdoori (13,780 ft) for snow vistas.' },
                    { time: '02:00 PM', activity: 'Hot Kahwa and Rogan Josh lunch at Nedous Hotel vintage colonial dining room.' },
                    { time: '06:00 PM', activity: 'Return drive to Srinagar watching shepherd flocks across green alpine meadows.' }
                ]
            },
            {
                day: 5,
                theme: 'Botanical Splendor & Floating Market Farewell',
                slots: [
                    { time: '08:30 AM', activity: 'Walk through Asia\'s largest tulip garden (Indira Gandhi Memorial) and Pari Mahal palace ruins.' },
                    { time: '11:30 AM', activity: 'Collect premium Kashmiri saffron, Mamra almonds, and walnut kernels in Lal Chowk.' },
                    { time: '02:00 PM', activity: 'Farewell feast with saffron Yakhni and Dum Aloo at Lhasa Tibetan & Kashmiri restaurant.' },
                    { time: '06:00 PM', activity: 'Peaceful final golden hour Shikara glide across Nigeen Lake tranquil waters.' }
                ]
            }
        ]
    },
    'shimla': {
        destination: 'Shimla & Kufri, Himachal',
        days: 4,
        style: 'Hills & Heritage',
        budget: 'Moderate',
        cost: '₹30,000',
        daysList: [
            {
                day: 1,
                theme: 'The Ridge, Mall Road & Colonial Icons',
                slots: [
                    { time: '08:30 AM', activity: 'Artisan crepes and mountain espresso at Wake & Bake Cafe on Mall Road.' },
                    { time: '10:30 AM', activity: 'Photograph Neo-Gothic Christ Church on The Ridge and hike up to Jakhu Temple Hanuman colossus.' },
                    { time: '02:00 PM', activity: 'Panoramic mountain lunch at Cafe Shimla Times overlooking the valley.' },
                    { time: '06:00 PM', activity: 'Evening stroll down heritage Gaiety Theatre quarter and hot Gulab Jamun at Baljees.' }
                ]
            },
            {
                day: 2,
                theme: 'Kufri Alpine Panoramas & Viceregal Lodge',
                slots: [
                    { time: '08:30 AM', activity: 'Drive through fragrant cedar forests to Kufri for horseback riding up Mahasu Peak.' },
                    { time: '01:30 PM', activity: 'Mountain lunch with hot Maggi and ginger tea overlooking the Pir Panjal snow ranges.' },
                    { time: '03:30 PM', activity: 'Explore Scottish baronial architecture of Indian Institute of Advanced Study (Viceregal Lodge).' },
                    { time: '06:30 PM', activity: 'Handmade pine and walnut wooden souvenir shopping at Lakkar Bazaar.' }
                ]
            },
            {
                day: 3,
                theme: 'Mashobra Pine Trails & Craignano',
                slots: [
                    { time: '09:00 AM', activity: 'Peaceful nature walk through cedar woods of Mashobra to Craignano apple orchards.' },
                    { time: '01:00 PM', activity: 'Picnic lunch surrounded by oak and rhododendron groves.' },
                    { time: '03:30 PM', activity: 'Forest hike down to Chadwick Falls cascading natural freshwater stream.' },
                    { time: '07:00 PM', activity: 'Live acoustic music and wood-fired pizza at Eighteen71 Cookhouse & Bar.' }
                ]
            },
            {
                day: 4,
                theme: 'Toy Train Romance & Mountain Farewell',
                slots: [
                    { time: '09:00 AM', activity: 'Scenic joyride on UNESCO Kalka-Shimla Toy Train crossing tunnels and arched stone bridges.' },
                    { time: '12:00 PM', activity: 'Shopping for Himachali handwoven shawls and fresh apple preserves on Mall Road.' },
                    { time: '02:30 PM', activity: 'Farewell lunch at The Restaurant at The Oberoi Cecil.' },
                    { time: '05:30 PM', activity: 'Sunset over snowy Himalayan foothills from Scandal Point promenade.' }
                ]
            }
        ]
    },
    'amritsar': {
        destination: 'Amritsar Golden Temple, Punjab',
        days: 3,
        style: 'Cultural & Spiritual',
        budget: 'Moderate',
        cost: '₹22,500',
        daysList: [
            {
                day: 1,
                theme: 'Golden Temple Sanctum, Sarovar & Langar',
                slots: [
                    { time: '07:30 AM', activity: 'Spiritual morning parikrama around sacred Amrit Sarovar and darshan inside Sri Harmandir Sahib.' },
                    { time: '10:30 AM', activity: 'Participate in Guru Ka Langar, world\'s largest community kitchen feeding thousands daily.' },
                    { time: '01:30 PM', activity: 'Crispy Amritsari Kulcha with melting butter and chole at Pehalwan Kulcha.' },
                    { time: '06:00 PM', activity: 'Evening Palki Sahib golden palanquin ceremony with soul-stirring Gurbani kirtan.' }
                ]
            },
            {
                day: 2,
                theme: 'Wagah Border Ceremony & Jallianwala Bagh',
                slots: [
                    { time: '09:00 AM', activity: 'Pay solemn tribute at Jallianwala Bagh national memorial and explore Partition Museum.' },
                    { time: '01:00 PM', activity: 'Legendary Dal Makhani and Firni lunch at Kesar Da Dhaba in Chowk Passian.' },
                    { time: '03:30 PM', activity: 'Scenic drive to Wagah-Attari Border for the high-octane Beating Retreat ceremony with roaring crowds.' },
                    { time: '08:00 PM', activity: 'Evening heritage walk and Phulkari embroidery shopping along illuminated Heritage Street.' }
                ]
            },
            {
                day: 3,
                theme: 'Historic Fortresses & Punjabi Heritage Village',
                slots: [
                    { time: '09:00 AM', activity: 'Explore Gobindgarh Fort, ancient coin museums, and martial Sikh warfare galleries.' },
                    { time: '01:00 PM', activity: 'Authentic Amritsari fish fry and butter chicken feast at Makhan Fish & Chicken Corner.' },
                    { time: '03:30 PM', activity: 'Cultural tour of Sadda Pind heritage village experiencing Bhangra and pottery making.' },
                    { time: '07:00 PM', activity: 'Tall brass glass of creamy sweet Amritsari Lassi at Ahuja Milk Centre.' }
                ]
            }
        ]
    },
    'rishikesh': {
        destination: 'Rishikesh Yoga Capital, Uttarakhand',
        days: 4,
        style: 'Spiritual & Adventure',
        budget: 'Moderate',
        cost: '₹30,000',
        daysList: [
            {
                day: 1,
                theme: 'Holy Ganges Rapids, Suspension Bridges & Ashrams',
                slots: [
                    { time: '08:00 AM', activity: 'Aloo Poori breakfast with herbal ginger tea at Chotiwala Restaurant near Ram Jhula.' },
                    { time: '10:00 AM', activity: 'Walk across iconic suspension bridges Laxman Jhula & Ram Jhula watching sacred river currents.' },
                    { time: '01:30 PM', activity: 'Healthy organic Ayurvedic lunch and kombucha at The 60\'s Beatles Cafe in Tapovan.' },
                    { time: '05:30 PM', activity: 'Spiritual Maha Aarti ceremony with glowing diyas and holy Vedic chants at Triveni Ghat.' }
                ]
            },
            {
                day: 2,
                theme: 'White-Water Rafting & Cliff Jumps',
                slots: [
                    { time: '08:30 AM', activity: 'Adrenaline-fueled 16-km white-water river rafting expedition through rapids like Roller Coaster.' },
                    { time: '01:00 PM', activity: 'Riverside Maggi and lemon tea at Marine Drive beach camp.' },
                    { time: '03:30 PM', activity: 'Explore graffiti-covered meditation domes of historic Beatles Ashram (Chaurasi Kutia).' },
                    { time: '06:30 PM', activity: 'Sunset acoustic music session at Little Buddha Cafe overlooking emerald Ganges.' }
                ]
            },
            {
                day: 3,
                theme: 'Sunrise Peak Shrines & Waterfalls',
                slots: [
                    { time: '05:30 AM', activity: 'Early morning drive to Kunjapuri Devi Temple for sunrise over snow-capped Himalayan peaks.' },
                    { time: '09:00 AM', activity: 'Hike through lush forest to cascading Neer Garh waterfalls and crystal pools.' },
                    { time: '01:30 PM', activity: 'Rooftop lunch at Pure Soul Cafe overlooking the valley.' },
                    { time: '05:30 PM', activity: 'Evening riverside meditation and sound bowl healing by the holy Ganges.' }
                ]
            },
            {
                day: 4,
                theme: 'Ganga Beach Camping & Farewell Aarti',
                slots: [
                    { time: '08:30 AM', activity: 'Morning yoga session on white sand beach of the Ganges.' },
                    { time: '11:00 AM', activity: 'Visit Vashishta Gufa ancient meditation cave right beside the river.' },
                    { time: '02:00 PM', activity: 'Wood-fired Italian pizza at Bistro Nirvana in Tapovan.' },
                    { time: '06:00 PM', activity: 'Parmarth Niketan sunset Ganga Aarti with devotional chants and brass lamps.' }
                ]
            }
        ]
    },
    'agra': {
        destination: 'Agra & Taj Mahal, Uttar Pradesh',
        days: 3,
        style: 'Mughal Heritage',
        budget: 'Moderate',
        cost: '₹22,500',
        daysList: [
            {
                day: 1,
                theme: 'The Wonder of Taj Mahal & Mughal Splendor',
                slots: [
                    { time: '05:45 AM', activity: 'Sunrise entry to Taj Mahal, witnessing white marble change hues in first morning light.' },
                    { time: '09:00 AM', activity: 'Traditional Bedai and spicy Jalebi breakfast at Deviram Sweets on Pratap Pura.' },
                    { time: '11:00 AM', activity: 'Explore red sandstone ramparts, Diwan-i-Khas, and Sheesh Mahal at historic Agra Fort.' },
                    { time: '05:30 PM', activity: 'Golden hour sunset reflections of Taj Mahal from across Yamuna River at Mehtab Bagh.' }
                ]
            },
            {
                day: 2,
                theme: 'Imperial Ghost City of Fatehpur Sikri',
                slots: [
                    { time: '08:30 AM', activity: 'Scenic drive to UNESCO Fatehpur Sikri, emperor Akbar\'s majestic 16th-century capital.' },
                    { time: '10:30 AM', activity: 'Walk through colossal Buland Darwaza and offer prayers at marble tomb of Salim Chishti.' },
                    { time: '02:00 PM', activity: 'Mughlai kebab and biryani feast at Pinch of Spice on Fatehabad Road.' },
                    { time: '05:30 PM', activity: 'Visit Itmad-ud-Daulah (\'Baby Taj\'), admiring exquisite Pietra Dura marble inlays.' }
                ]
            },
            {
                day: 3,
                theme: 'Mughal Gardens & Artisan Bazaars',
                slots: [
                    { time: '09:00 AM', activity: 'Visit emperor Akbar\'s red sandstone and white marble mausoleum at Sikandra in deer park.' },
                    { time: '12:00 PM', activity: 'Explore Kinari Bazaar for zardozi embroidery and leather handcrafted footwear.' },
                    { time: '02:30 PM', activity: 'Sample authentic Angoori and Kesar Petha at historic Panchhi Petha.' },
                    { time: '06:00 PM', activity: 'Rooftop dinner at Bellevue with distant illuminated views of the Taj Mahal.' }
                ]
            }
        ]
    },
    'jodhpur': {
        destination: 'Jodhpur Blue City, Rajasthan',
        days: 4,
        style: 'Heritage & Desert',
        budget: 'Moderate',
        cost: '₹30,000',
        daysList: [
            {
                day: 1,
                theme: 'Mehrangarh Citadel & Blue Alleys',
                slots: [
                    { time: '08:30 AM', activity: 'Famous Shahi Samosa and Makhaniya Lassi breakfast at Clock Tower bazaar.' },
                    { time: '10:00 AM', activity: 'Ascend colossal Mehrangarh Fort towering 400 ft above the skyline, visiting royal palanquins.' },
                    { time: '02:00 PM', activity: 'Traditional Rajasthani Ker Sangri and Dal Baati Churma at Gypsy Dining Hall.' },
                    { time: '05:30 PM', activity: 'Walk through indigo-painted Brahmin alleys of Navchokiya to a rooftop sunset cafe.' }
                ]
            },
            {
                day: 2,
                theme: 'Marble Cenotaphs, Stepwells & Palaces',
                slots: [
                    { time: '09:00 AM', activity: 'Marvel at milky-white marble cenotaphs of Jaswant Thada and lake gardens.' },
                    { time: '11:30 AM', activity: 'Geometric architecture and cold brew at Toorji Ka Jhalra ancient stepwell.' },
                    { time: '02:30 PM', activity: 'Tour the opulent Art Deco museum at Umaid Bhawan Palace.' },
                    { time: '06:00 PM', activity: 'Brocade, bandhani, and spice shopping in Sardar Market under illuminated fort.' }
                ]
            },
            {
                day: 3,
                theme: 'Bishnoi Tribal Village Safari',
                slots: [
                    { time: '08:30 AM', activity: 'Open-top 4x4 jeep safari to rural Bishnoi villages observing blackbucks and chinkaras.' },
                    { time: '11:30 AM', activity: 'Watch master potters and durrie rug weavers at work in Salawas village.' },
                    { time: '02:00 PM', activity: 'Traditional village lunch prepared over earthen chulha with bajra roti and ghee.' },
                    { time: '06:00 PM', activity: 'Sunset over Kaylana Lake watching migratory birds.' }
                ]
            },
            {
                day: 4,
                theme: 'Mandore Gardens & Royal Farewell',
                slots: [
                    { time: '09:00 AM', activity: 'Explore ornate rock-carved cenotaphs and temples amidst lush Mandore Gardens.' },
                    { time: '12:30 PM', activity: 'Mirchi Vada and Mawa Kachori tasting at Janta Sweet Home.' },
                    { time: '03:00 PM', activity: 'Browse antique brass artifacts and carved wooden furniture in old city shops.' },
                    { time: '06:30 PM', activity: 'Farewell rooftop candlelight feast at Indique overlooking glowing Mehrangarh.' }
                ]
            }
        ]
    },
    'jaisalmer': {
        destination: 'Jaisalmer Golden City, Rajasthan',
        days: 4,
        style: 'Desert & Heritage',
        budget: 'Moderate',
        cost: '₹30,000',
        daysList: [
            {
                day: 1,
                theme: 'The Living Sandstone Fort (Sonar Qila)',
                slots: [
                    { time: '08:30 AM', activity: 'Breakfast on fort ramparts at Jaisal Italy with sweeping golden city panoramas.' },
                    { time: '10:00 AM', activity: 'Guided walking tour through Jaisalmer Fort, home to 3,000 residents inside medieval ramparts.' },
                    { time: '02:00 PM', activity: 'Traditional Rajasthani Gatte Ki Sabzi and Bajra Roti at The Trio.' },
                    { time: '05:30 PM', activity: 'Sunset rowboat cruise across sacred Gadisar Lake surrounded by carved temples.' }
                ]
            },
            {
                day: 2,
                theme: 'Thar Desert Dunes, Camels & Campfire',
                slots: [
                    { time: '09:00 AM', activity: 'Explore intricate yellow sandstone carvings of Patwon Ki Haveli and Salim Singh Ki Haveli.' },
                    { time: '01:30 PM', activity: 'Scenic drive into Thar Desert, stopping at haunted ruins of Kuldhara village.' },
                    { time: '04:30 PM', activity: 'Sunset camel safari across the rolling ripples of Sam Sand Dunes.' },
                    { time: '08:00 PM', activity: 'Desert camp musical evening with Kalbelia folk dancers, fire acrobatics, and stargazing.' }
                ]
            },
            {
                day: 3,
                theme: 'Royal Cenotaphs & Desert National Park',
                slots: [
                    { time: '08:30 AM', activity: 'Early morning photography at golden carved cenotaphs of Bada Bagh.' },
                    { time: '11:00 AM', activity: 'Expedition to Desert National Park spotting Great Indian Bustards and desert foxes.' },
                    { time: '02:30 PM', activity: 'Rustic campfire lunch under desert Khejri trees.' },
                    { time: '06:00 PM', activity: 'Sunset views from Vyas Chhatri marble cenotaph ridge overlooking the Golden City.' }
                ]
            },
            {
                day: 4,
                theme: 'Thar Handicrafts & Citadel Farewell',
                slots: [
                    { time: '09:30 AM', activity: 'Explore Lodurva ancient Jain temple complex with ornate silver kalpvriksha tree.' },
                    { time: '12:30 PM', activity: 'Shopping for handcrafted camel leather journals, mirror-work textiles, and fossil stone.' },
                    { time: '03:00 PM', activity: 'Ghotua Laddu tasting at historic local confectionery.' },
                    { time: '06:30 PM', activity: 'Farewell dinner at Pleasant Haveli rooftop with golden night illumination.' }
                ]
            }
        ]
    },
    'hampi': {
        destination: 'Hampi UNESCO Ruins, Karnataka',
        days: 3,
        style: 'Heritage & Adventure',
        budget: 'Moderate',
        cost: '₹22,500',
        daysList: [
            {
                day: 1,
                theme: 'Sacred Centre, Tungabhadra & Boulders',
                slots: [
                    { time: '06:00 AM', activity: 'Sunrise hike up Matanga Hill overlooking a sea of granite boulders and ancient ruins.' },
                    { time: '08:30 AM', activity: 'Traditional South Indian breakfast at Mango Tree restaurant.' },
                    { time: '10:30 AM', activity: 'Explore active 7th-century Virupaksha Temple and monolithic Sasivekalu Ganesha.' },
                    { time: '04:30 PM', activity: 'Coracle round-boat ride on Tungabhadra River and golden hour sunset at Hemakuta Hill.' }
                ]
            },
            {
                day: 2,
                theme: 'Vijayanagara Empire, Stone Chariot & Royal Enclosure',
                slots: [
                    { time: '08:30 AM', activity: 'Marvel at iconic Stone Chariot and musical acoustic pillars at Vijaya Vittala Temple.' },
                    { time: '12:00 PM', activity: 'Explore Indo-Islamic pavilions of Lotus Mahal and colossal Elephant Stables.' },
                    { time: '02:30 PM', activity: 'Traditional banana-leaf thali at local village cafe in Kamalapur.' },
                    { time: '05:30 PM', activity: 'Sunset vistas across the Tungabhadra valley from Malyavanta Raghunatha Temple.' }
                ]
            },
            {
                day: 3,
                theme: 'Anegundi Village, Monkey Hill & Bouldering',
                slots: [
                    { time: '06:30 AM', activity: 'Climb 575 stone steps to Anjaneya Hill (birthplace of Hanuman) for panoramic sunrise.' },
                    { time: '09:30 AM', activity: 'Explore ancient rural lanes and stone houses of Anegundi heritage village.' },
                    { time: '01:00 PM', activity: 'Wood-fired sourdough pizza and iced coffee at German Bakery.' },
                    { time: '05:00 PM', activity: 'Sanapur Lake cliff jumping and boulder-hopping before farewell riverside dinner.' }
                ]
            }
        ]
    },
    'ooty': {
        destination: 'Ooty Queen of Nilgiris, Tamil Nadu',
        days: 3,
        style: 'Misty Hills & Nature',
        budget: 'Moderate',
        cost: '₹22,500',
        daysList: [
            {
                day: 1,
                theme: 'Heritage Nilgiri Toy Train & Botanical Gardens',
                slots: [
                    { time: '08:30 AM', activity: 'Scenic ride aboard UNESCO Nilgiri Mountain Railway heritage steam train over viaducts.' },
                    { time: '11:00 AM', activity: 'Walk through lush terraced lawns and fossil tree trunks of Government Botanical Garden.' },
                    { time: '01:30 PM', activity: 'Colonial high tea and lunch at Earl\'s Secret heritage bungalow.' },
                    { time: '05:00 PM', activity: 'Leisurely rowboat cruise on misty Ooty Lake and handmade fudge shopping at King Star.' }
                ]
            },
            {
                day: 2,
                theme: 'Highest Peak & Tea Estates',
                slots: [
                    { time: '08:30 AM', activity: 'Ascend Doddabetta Peak (8,650 ft), highest point in Nilgiris, for telescope valley views.' },
                    { time: '11:30 AM', activity: 'Doddabetta Tea Factory & Chocolate Museum tasting hot artisanal Nilgiri tea.' },
                    { time: '02:30 PM', activity: 'Pykara Lake speedboating and pine forest walk along Pykara waterfalls.' },
                    { time: '06:00 PM', activity: 'Evening shopping for pure eucalyptus oil, homemade chocolates, and spices in Commercial Street.' }
                ]
            },
            {
                day: 3,
                theme: 'Avalanche Lake & Shola Forests',
                slots: [
                    { time: '08:30 AM', activity: 'Offbeat jeep expedition to pristine Avalanche Lake surrounded by rhododendrons and sholas.' },
                    { time: '12:30 PM', activity: 'Lakeside picnic with Nilgiri cheeses and fresh bakery baguettes.' },
                    { time: '03:00 PM', activity: 'Emerald Lake tea estate vista point photography.' },
                    { time: '06:30 PM', activity: 'Farewell Chinese dinner at historic Shinkows restaurant on Commissioner\'s Road.' }
                ]
            }
        ]
    },
    'darjeeling': {
        destination: 'Darjeeling Tea Hills, West Bengal',
        days: 3,
        style: 'Mountain & Tea Hills',
        budget: 'Moderate',
        cost: '₹22,500',
        daysList: [
            {
                day: 1,
                theme: 'Tiger Hill Sunrise & Himalayan Masters',
                slots: [
                    { time: '04:00 AM', activity: 'Dawn ascent to Tiger Hill watching sunrise illuminate snow-capped Mount Kanchenjunga (8,586 m).' },
                    { time: '08:30 AM', activity: 'Ghoom Monastery prayer wheels, Batasia Loop railway spiral, and Glenary\'s bakery breakfast.' },
                    { time: '11:30 AM', activity: 'Himalayan Mountaineering Institute (HMI) museum & Himalayan Zoo spotting Red Pandas.' },
                    { time: '05:30 PM', activity: 'Evening walk on Chowrasta Mall Road with hot momos and Darjeeling Muscatel tea.' }
                ]
            },
            {
                day: 2,
                theme: 'Happy Valley Tea & Japanese Peace Pagoda',
                slots: [
                    { time: '09:00 AM', activity: 'Heritage walk through Happy Valley Tea Estate witnessing organic Darjeeling tea plucking.' },
                    { time: '01:00 PM', activity: 'Keventers rooftop English breakfast and hot cocoa overlooking mountain peaks.' },
                    { time: '03:30 PM', activity: 'Peaceful chanting at Japanese Peace Pagoda and scenic Darjeeling Ropeway cable car glide.' },
                    { time: '06:30 PM', activity: 'Sunset over tea valleys from Observatory Hill.' }
                ]
            },
            {
                day: 3,
                theme: 'Rock Garden & Colonial Heritage Farewell',
                slots: [
                    { time: '09:00 AM', activity: 'Drive down steep hillside hairpins to tiered waterfalls of Barbotey Rock Garden.' },
                    { time: '01:00 PM', activity: 'Tibetan Thukpa and Shaphalay lunch at Kunga Restaurant.' },
                    { time: '03:30 PM', activity: 'Purchase first-flush orthodox tea tins at Nathmulls Tea Lounge on The Mall.' },
                    { time: '06:30 PM', activity: 'Live jazz music and colonial dinner at Glenary\'s Restaurant & Pub.' }
                ]
            }
        ]
    },
    'pondicherry': {
        destination: 'Pondicherry French Quarter, Tamil Nadu',
        days: 3,
        style: 'Coastal & Bohemian',
        budget: 'Moderate',
        cost: '₹22,500',
        daysList: [
            {
                day: 1,
                theme: 'White Town French Quarters & Promenade',
                slots: [
                    { time: '08:30 AM', activity: 'Artisanal French baguettes and cafe au lait at Cafe des Arts in White Town.' },
                    { time: '10:30 AM', activity: 'Walking tour of mustard-yellow colonial villas, bougainvillea gates, and French street signs.' },
                    { time: '01:30 PM', activity: 'French-Creole lunch at Coromandel Cafe.' },
                    { time: '05:30 PM', activity: 'Sunset seaside stroll along Goubert Promenade and peaceful meditation at Sri Aurobindo Ashram.' }
                ]
            },
            {
                day: 2,
                theme: 'Auroville Universal Township & Golden Globe',
                slots: [
                    { time: '08:30 AM', activity: 'Drive to Auroville, meditating with views of golden geodesic sphere Matrimandir.' },
                    { time: '01:00 PM', activity: 'Organic farm-to-table lunch at Solar Kitchen.' },
                    { time: '03:30 PM', activity: 'Boat ride through Chunnambar backwaters to isolated Paradise Beach sand spit.' },
                    { time: '07:00 PM', activity: 'Wood-fired sourdough pizza and gelato at Tanto Pizzeria.' }
                ]
            },
            {
                day: 3,
                theme: 'Gothic Cathedrals & Serenity Beach',
                slots: [
                    { time: '08:30 AM', activity: 'Croissants and espresso at Baker Street French bakery on Bussy Street.' },
                    { time: '10:30 AM', activity: 'Visit Basilica of the Sacred Heart of Jesus admiring stained glass panels.' },
                    { time: '02:00 PM', activity: 'Surfing lesson and fresh seafood at Serenity Beach shack.' },
                    { time: '06:00 PM', activity: 'Sunset cocktails overlooking the Bay of Bengal at Promenade Hotel rooftop.' }
                ]
            }
        ]
    },
    'coorg': {
        destination: 'Coorg Scotland of India, Karnataka',
        days: 3,
        style: 'Hills & Coffee Estates',
        budget: 'Moderate',
        cost: '₹22,500',
        daysList: [
            {
                day: 1,
                theme: 'Coffee Plantations, Abbey Falls & Raja\'s Seat',
                slots: [
                    { time: '08:30 AM', activity: 'Authentic Akki Roti and filter coffee breakfast in Madikeri.' },
                    { time: '10:30 AM', activity: 'Guided walking tour through lush Arabica coffee and black pepper plantations.' },
                    { time: '02:00 PM', activity: 'Traditional Kodava Pandi Curry lunch at Coorg Cuisine.' },
                    { time: '05:30 PM', activity: 'Abbey Falls waterfall viewpoint through spice trees and sunset at Raja\'s Seat.' }
                ]
            },
            {
                day: 2,
                theme: 'Elephant Sanctuary & Golden Temple',
                slots: [
                    { time: '08:30 AM', activity: 'Morning visit to Dubare Elephant Camp watching elephants bathe in Cauvery river.' },
                    { time: '12:30 PM', activity: 'Explore Namdroling Monastery (Golden Temple) in Bylakuppe with 40-ft gilded Buddha statues.' },
                    { time: '03:00 PM', activity: 'Tibetan momos and thukpa at Camp 1.' },
                    { time: '06:00 PM', activity: 'Shopping for artisanal Coorg coffee beans, wild honey, and homemade chocolates.' }
                ]
            },
            {
                day: 3,
                theme: 'Mandalpatti Mist & Sacred Springs',
                slots: [
                    { time: '07:30 AM', activity: '4x4 open-top jeep adventure through rolling mist up to Mandalpatti Peak (4,050 ft).' },
                    { time: '11:30 AM', activity: 'Visit Talakaveri, sacred birthplace of River Cauvery in Brahmagiri hills.' },
                    { time: '02:30 PM', activity: 'Traditional vegetarian thali at Bhagamandala.' },
                    { time: '06:00 PM', activity: 'Farewell sunset overlooking emerald plantation valleys from Madikeri Fort.' }
                ]
            }
        ]
    },
    'mysore': {
        destination: 'Mysore Palace Heritage, Karnataka',
        days: 3,
        style: 'Royal & Heritage',
        budget: 'Moderate',
        cost: '₹22,500',
        daysList: [
            {
                day: 1,
                theme: 'Imperial Mysore Palace & Royal Markets',
                slots: [
                    { time: '08:30 AM', activity: 'Mylari Restaurant world-famous soft butter dosas with coconut chutney.' },
                    { time: '10:00 AM', activity: 'Extensive guided tour of magnificent Indo-Saracenic Mysore Palace and jewel-encrusted Durbar.' },
                    { time: '02:00 PM', activity: 'Royal dining at Lalitha Mahal Palace heritage hotel.' },
                    { time: '06:30 PM', activity: 'Witness breathtaking illumination of Mysore Palace with 97,000 glowing bulbs.' }
                ]
            },
            {
                day: 2,
                theme: 'Chamundi Hill, Sacred Nandi & Fountains',
                slots: [
                    { time: '08:30 AM', activity: 'Climb Chamundi Hill to Sri Chamundeshwari Temple and colossal 16-ft monolithic Nandi.' },
                    { time: '12:00 PM', activity: 'Color and aroma exploration in Devaraja Market with flower garlands and sandalwood.' },
                    { time: '03:00 PM', activity: 'Taste authentic melt-in-mouth Mysore Pak at Guru Sweet Mart where it was invented.' },
                    { time: '06:30 PM', activity: 'Evening dancing musical fountain spectacle at Brindavan Gardens.' }
                ]
            },
            {
                day: 3,
                theme: 'Tipu Sultan\'s Island Fortress & Silk Weavers',
                slots: [
                    { time: '09:00 AM', activity: 'Visit Srirangapatna island fort, Dariya Daulat Bagh summer palace, and Gumbaz mausoleum.' },
                    { time: '01:00 PM', activity: 'Traditional Karnataka ragi mudde and mutton saaru lunch at Hotel RRR.' },
                    { time: '03:30 PM', activity: 'Visit Mysore Silk factory observing pure mulberry silk weaving with gold zari.' },
                    { time: '06:30 PM', activity: 'Farewell walk along Karanji Lake watching painted storks and pelicans.' }
                ]
            }
        ]
    }
};

window.currentItineraryDest = 'Jaipur, Rajasthan';
window.currentItineraryDays = 5;

// Intelligent preset lookup supporting substring matches & regional aliases
function findMatchedPreset(dest) {
    if (!dest) return null;
    const destNorm = dest.toLowerCase();

    for (const key of Object.keys(SAMPLE_ITINERARY_PRESETS)) {
        if (destNorm.includes(key) || key.includes(destNorm.split(',')[0].trim().toLowerCase())) {
            return SAMPLE_ITINERARY_PRESETS[key];
        }
    }

    const aliases = {
        'kashmir': 'srinagar',
        'pahalgam': 'srinagar',
        'gulmarg': 'srinagar',
        'sonamarg': 'srinagar',
        'leh': 'ladakh',
        'nubra': 'ladakh',
        'munnar': 'kerala',
        'alleppey': 'kerala',
        'kochi': 'kerala',
        'kaza': 'manali',
        'mcleodganj': 'manali',
        'kufri': 'shimla',
        'rohtang': 'manali',
        'taj': 'agra',
        'vrindavan': 'varanasi',
        'mathura': 'varanasi',
        'ayodhya': 'varanasi',
        'meghalaya': 'darjeeling',
        'cherrapunji': 'darjeeling',
        'shillong': 'darjeeling',
        'landour': 'shimla',
        'mussoorie': 'shimla',
        'nainital': 'shimla',
        'havelock': 'goa',
        'andaman': 'goa',
        'gokarna': 'goa',
        'hampi': 'hampi',
        'ooty': 'ooty',
        'coorg': 'coorg',
        'mysore': 'mysore',
        'jodhpur': 'jodhpur',
        'jaisalmer': 'jaisalmer',
        'amritsar': 'amritsar',
        'rishikesh': 'rishikesh',
        'haridwar': 'rishikesh',
        'pondicherry': 'pondicherry'
    };

    for (const [token, mappedKey] of Object.entries(aliases)) {
        if (destNorm.includes(token) && SAMPLE_ITINERARY_PRESETS[mappedKey]) {
            return SAMPLE_ITINERARY_PRESETS[mappedKey];
        }
    }

    return null;
}

function buildDaysTimelineHtml(daysList) {
    let daysHtml = '';
    daysList.forEach((dayObj, idx) => {
        const dayNum = dayObj.day || (idx + 1);
        const dayFormatted = String(dayNum).padStart(2, '0');
        const dayTheme = dayObj.theme || dayObj.title || `Day ${dayNum} Exploration`;
        const slots = dayObj.slots || dayObj.activities || [];

        let slotsHtml = '';
        slots.forEach(slot => {
            const time = slot.time || '';
            const activity = slot.activity || slot.text || '';
            slotsHtml += `
                <li class="activity-item">
                    <span class="time-tag">${escapeReviewText(time)}</span>
                    <span class="activity-desc">${escapeReviewText(activity)}</span>
                </li>
            `;
        });

        daysHtml += `
            <div class="day-block">
                <div class="day-title-row">
                    <span class="day-pill">DAY ${dayFormatted}</span>
                    <span class="day-theme">${escapeReviewText(dayTheme)}</span>
                </div>
                <ul class="activity-list">
                    ${slotsHtml}
                </ul>
            </div>
        `;
    });
    return daysHtml;
}

function renderRealItinerary(destination, days, itineraryDays, aiEngine, style, budget) {
    const itineraryOutput = document.getElementById('itineraryOutput');
    if (!itineraryOutput) return;

    const effStyle = style || 'Adventure';
    const effBudget = budget || 'Moderate';

    window.currentItineraryDest = destination;
    window.currentItineraryDays = days;

    const daysHtml = buildDaysTimelineHtml(itineraryDays);
    const perDayMap = { 'Budget': 3500, 'Moderate': 7500, 'Luxury': 16000, 'Ultra-Bespoke': 35000 };
    const perDay = perDayMap[effBudget] || 7500;
    const estCost = `₹${(days * perDay).toLocaleString('en-IN')}`;

    itineraryOutput.innerHTML = `
        <!-- Real-Time "Little Reload" Overlay -->
        <div class="planner-reload-overlay" id="plannerReloadOverlay">
            <div class="reload-spinner-glow">
                <div class="reload-spinner-core"></div>
                <span class="reload-spinner-icon">⚡</span>
            </div>
            <div class="reload-text-group">
                <h4 id="reloadTitleDisplay">Updating Itinerary...</h4>
                <p id="reloadSubtextDisplay">Recalibrating route &amp; daily schedule</p>
            </div>
        </div>

        <div class="itinerary-container" id="itineraryContainer" style="animation: heroEntrance 0.6s cubic-bezier(0.16, 1, 0.3, 1);">
            <div class="itinerary-header">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.35rem; flex-wrap: wrap;">
                        <span class="section-tag" style="margin-bottom: 0;">TravelMate AI Itinerary</span>
                        <span class="itinerary-badge" style="background: rgba(0, 242, 254, 0.12); color: #00f2fe; border: 1px solid rgba(0, 242, 254, 0.35);" id="itineraryStatusBadge">
                            ⚡ AI Tailored Route
                        </span>
                    </div>
                    <h3 id="itineraryTitleDisplay">${escapeReviewText(destination)} (${days} Days)</h3>
                    <p style="color: #94a3b8; font-size: 0.88rem; margin-top: 0.2rem;" id="itinerarySubtitleDisplay">
                        Archetype: <strong style="color: #38bdf8;" id="itineraryStyleDisplay">${escapeReviewText(effStyle)}</strong> • 
                        Budget: <strong style="color: #818cf8;" id="itineraryBudgetDisplay">${escapeReviewText(effBudget)}</strong> (~${estCost})
                    </p>
                </div>
                <span class="itinerary-badge" id="itineraryEngineBadge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.35);">
                    ⚡ ${escapeReviewText(aiEngine || 'TravelMate AI Ready')}
                </span>
            </div>

            <div class="day-timeline custom-scrollbar" id="dayTimelineContainer">
                ${daysHtml}
            </div>

            <div class="itinerary-actions">
                <button type="button" class="btn-login" style="cursor: pointer;" onclick="saveItinerary('${escapeReviewText(destination)}')">
                    💾 Save Itinerary
                </button>
                <button type="button" class="btn-card-action" style="cursor: pointer;" onclick="handleExportPDF('${escapeReviewText(destination)}', ${days})">
                    🖨️ Export PDF
                </button>
                <button type="button" class="btn-card-action" style="cursor: pointer; background: linear-gradient(135deg, rgba(0, 242, 254, 0.2), rgba(79, 70, 229, 0.2)); border-color: rgba(0, 242, 254, 0.4); color: #00f2fe;" onclick="window.fetchDynamicItinerary('${escapeReviewText(destination)}', ${days})">
                    🔄 Regenerate Plan
                </button>
            </div>
        </div>
    `;
    syncPlannerCardHeights();
}

function generateProceduralDummyDays(dest, days, style, budget) {
    const cleanCity = (dest || 'Destination').split(',')[0].trim();
    const stateName = (dest || '').includes(',') ? dest.split(',')[1].trim() : '';
    const destLower = dest.toLowerCase();
    const result = [];
    const st = style || 'Adventure';
    const bg = budget || 'Moderate';

    // Contextual theme detection
    let isMountain = destLower.includes('valley') || destLower.includes('pass') || destLower.includes('himachal') || destLower.includes('kashmir') || destLower.includes('hill') || destLower.includes('trek') || destLower.includes('meadow') || destLower.includes('auli');
    let isFortHeritage = destLower.includes('fort') || destLower.includes('rajasthan') || destLower.includes('palace') || destLower.includes('wall') || destLower.includes('haveli') || destLower.includes('citadel') || destLower.includes('jaipur') || destLower.includes('udaipur') || destLower.includes('jodhpur');
    let isSpiritual = destLower.includes('temple') || destLower.includes('ghat') || destLower.includes('shrine') || destLower.includes('dham') || destLower.includes('holy') || destLower.includes('kashi') || destLower.includes('aarti') || destLower.includes('varanasi') || destLower.includes('rishikesh') || destLower.includes('amritsar');
    let isCoastal = destLower.includes('coast') || destLower.includes('beach') || destLower.includes('backwaters') || destLower.includes('island') || destLower.includes('sea') || destLower.includes('ocean') || destLower.includes('goa') || destLower.includes('kerala') || destLower.includes('andaman');
    let isSafari = destLower.includes('safari') || destLower.includes('national park') || destLower.includes('tiger') || destLower.includes('reserve') || destLower.includes('sanctuary');

    // Themes tailored to style
    let themes;
    if (st === 'Cultural') {
        themes = [
            `Historic Foundations & Heritage Monoliths of ${cleanCity}`,
            `Architectural Marvels, Stepwells & Dynastic Palaces`,
            `Artisan Quarters, Classical Crafts & Folklore in ${cleanCity}`,
            `Sacred Shrines, Heritage Museums & Ancient Quarters`,
            `Cultural Feasting, Spice Bazaars & Evening Symphony in ${cleanCity}`,
            `Royal Citadel Walls & Living Heritage Enclaves around ${cleanCity}`,
            `Centuries-Old Traditions & Farewell Gala in ${cleanCity}`
        ];
    } else if (st === 'Romantic') {
        themes = [
            `Enchanted Arrival & Scenic Sunset Panoramas in ${cleanCity}`,
            `Tranquil Courtyards, Secluded Viewpoints & Serenade Dining`,
            `Idyllic Nature Escapes & Lakeside Vistas in ${cleanCity}`,
            `Heritage Romance, Candlelit Terraces & Starry Strolls`,
            `Private Artisan Discoveries & Twilight Moments in ${cleanCity}`,
            `Hidden Sanctuaries & Serene Horizons around ${cleanCity}`,
            `Intimate Farewells & Golden Hour Reflections in ${cleanCity}`
        ];
    } else if (st === 'Relaxed') {
        themes = [
            `Unhurried Arrival & Gentle Orientation in ${cleanCity}`,
            `Serene Garden Sanctuaries & Artisanal Tea Lounges`,
            `Scenic Leisure Promenade & Slow-Travel Exploration of ${cleanCity}`,
            `Wellness Retreats, Riverside Breezes & Quiet Heritage`,
            `Peaceful Bazaars, Local Delicacies & Sunset Contemplation`,
            `Verdant Countryside Retreats & Fresh Horizons near ${cleanCity}`,
            `Rejuvenating Farewell & Relaxed Leisure Morning in ${cleanCity}`
        ];
    } else { // Adventure
        themes = [
            `High-Energy Arrival & Rampart Trails in ${cleanCity}`,
            `Epic Viewpoint Hikes & Ridge Exploration around ${cleanCity}`,
            `Thrilling Backroads, Mountain Gorges & Canyon Treks`,
            `Hidden Caves, Stepwell Descents & Outdoor Expeditions`,
            `Vibrant Bazaar Quarters, Night Safaris & Street Trails`,
            `High-Altitude Horizons & Off-Grid Tracks around ${cleanCity}`,
            `Summit Sunrise & Adrenaline Farewell Gala in ${cleanCity}`
        ];
    }

    for (let i = 1; i <= days; i++) {
        const themeIndex = (i - 1) % themes.length;
        let diningNote = 'local signature dining';
        let morningStyle = 'artisanal breakfast';

        if (bg === 'Budget') {
            diningNote = 'authentic street food stalls & budget backpacker dhaba';
            morningStyle = 'piping-hot local kachori/chai and street-side breakfast';
        } else if (bg === 'Luxury') {
            diningNote = '5-star heritage palace fine-dining';
            morningStyle = 'luxurious continental & royal regional breakfast buffet';
        } else if (bg === 'Ultra-Bespoke') {
            diningNote = 'exclusive private chef banquet in a secluded palace courtyard';
            morningStyle = 'champagne breakfast with panoramic private terrace views';
        } else {
            diningNote = 'charming boutique cafe featuring regional specialties';
            morningStyle = 'artisanal breakfast with specialty coffee and local savories';
        }

        let morningAct, middayAct, lunchAct, eveningAct;
        if (isMountain) {
            morningAct = `${morningStyle} overlooking mist-shrouded cedar valleys of ${cleanCity}.`;
            middayAct = st === 'Adventure'
                ? `High-altitude ridge trek along pine-lined trails with panoramic Himalayan peaks.`
                : `Scenic nature stroll through pine woods exploring tranquil viewpoints of ${cleanCity}.`;
            lunchAct = `Warm mountain feast with piping-hot soup and momos at ${diningNote}.`;
            eveningAct = `Breathtaking sunset vista over Himalayan snow peaks followed by cozy fireside acoustic melodies.`;
        } else if (isFortHeritage) {
            morningAct = `${morningStyle} at an iconic heritage eatery in central ${cleanCity}.`;
            middayAct = st === 'Adventure'
                ? `Ramparts climb and fort battlements exploration across the ancient fortress of ${cleanCity}.`
                : `Guided heritage tour through mirror palaces, royal courtyards, and museum galleries of ${cleanCity}.`;
            lunchAct = `Royal heritage thali lunch feast at ${diningNote}.`;
            eveningAct = `Golden hour ramparts photography from high citadel bastions followed by handicraft and gemstone bazaars.`;
        } else if (isSpiritual) {
            morningAct = `Serene dawn prayers and peaceful walk along the sacred shrines and historic precincts of ${cleanCity}.`;
            middayAct = `Guided heritage walk exploring sacred temple corridors and centuries-old architectural sanctums.`;
            lunchAct = `Traditional sattvic thali banquet served with fresh local sweets at ${diningNote}.`;
            eveningAct = `Mesmerizing evening Maha Aarti ceremony with glowing brass lamps, bells, and riverfront chanting.`;
        } else if (isCoastal) {
            morningAct = `${morningStyle} along the coastal promenade of ${cleanCity}.`;
            middayAct = st === 'Adventure'
                ? `Watersports, kayaking, and coastal defense fort trek along the rocky headlands of ${cleanCity}.`
                : `Explore secluded crescent bays, historic lighthouses, and colonial maritime landmarks of ${cleanCity}.`;
            lunchAct = `Fresh coastal catch-of-the-day curry feast at ${diningNote}.`;
            eveningAct = `Spectacular clifftop ocean sunset with live acoustic sundowners and fresh seafood.`;
        } else if (isSafari) {
            morningAct = `Dawn 4x4 open-top wildlife safari tracking indigenous fauna in the wilderness of ${cleanCity}.`;
            middayAct = `Guided nature interpretation center tour and birdwatching walk along forest riverbanks.`;
            lunchAct = `Rustic wilderness feast featuring organic regional specialties at ${diningNote}.`;
            eveningAct = `Sunset watchtower wildlife photography followed by fireside naturalist tales under starry skies.`;
        } else {
            morningAct = `${morningStyle} in the heart of ${cleanCity}.`;
            middayAct = `Guided exploration of the premier historic landmarks and cultural monuments of ${cleanCity}.`;
            lunchAct = `Authentic regional culinary tasting lunch at ${diningNote}.`;
            eveningAct = `Scenic golden hour sunset photography followed by vibrant evening cultural walks in ${cleanCity}.`;
        }

        result.push({
            day: i,
            theme: themes[themeIndex],
            slots: [
                { time: '08:30 AM', activity: morningAct },
                { time: '11:00 AM', activity: middayAct },
                { time: '02:00 PM', activity: lunchAct },
                { time: '06:00 PM', activity: eveningAct }
            ]
        });
    }
    return result;
}

function renderFallbackItinerary(destination, days, style, budget) {
    const matchedPreset = findMatchedPreset(destination);
    const effStyle = style || 'Adventure';
    const effBudget = budget || 'Moderate';

    let daysList;
    if (matchedPreset && matchedPreset.daysList && (!style || style === 'Cultural' || style === matchedPreset.style)) {
        daysList = matchedPreset.daysList.slice(0, days);
        if (daysList.length < days) {
            const extra = generateProceduralDummyDays(destination, days - daysList.length, effStyle, effBudget);
            daysList = daysList.concat(extra.map((d, i) => ({ ...d, day: daysList.length + i + 1 })));
        }
    } else {
        daysList = generateProceduralDummyDays(destination, days, effStyle, effBudget);
    }

    renderRealItinerary(destination, days, daysList, 'TravelMate AI (Neural Sync)', effStyle, effBudget);
}

window.renderDummyItinerary = function(dest, days, style, budget) {
    const effStyle = style || 'Adventure';
    const effBudget = budget || 'Moderate';
    const matchedPreset = findMatchedPreset(dest);

    let daysList;
    if (matchedPreset && matchedPreset.daysList && (!style || style === 'Cultural' || style === matchedPreset.style)) {
        daysList = matchedPreset.daysList.slice(0, days);
        if (daysList.length < days) {
            const extra = generateProceduralDummyDays(dest, days - daysList.length, effStyle, effBudget);
            daysList = daysList.concat(extra.map((d, i) => ({ ...d, day: daysList.length + i + 1 })));
        }
    } else {
        daysList = generateProceduralDummyDays(dest, days, effStyle, effBudget);
    }

    const titleEl = document.getElementById('itineraryTitleDisplay');
    const subtitleEl = document.getElementById('itinerarySubtitleDisplay');
    const timelineEl = document.getElementById('dayTimelineContainer');
    const engineBadgeEl = document.getElementById('itineraryEngineBadge');

    // If DOM elements were replaced or missing, call renderRealItinerary to reconstruct cleanly!
    if (!titleEl || !timelineEl) {
        renderRealItinerary(dest, days, daysList, 'TravelMate AI Ready', effStyle, effBudget);
        return;
    }

    window.currentItineraryDest = dest;
    window.currentItineraryDays = days;

    const perDayMap = { 'Budget': 3500, 'Moderate': 7500, 'Luxury': 16000, 'Ultra-Bespoke': 35000 };
    const perDay = perDayMap[effBudget] || 7500;
    const estCost = `₹${(days * perDay).toLocaleString('en-IN')}`;

    titleEl.textContent = `${dest} (${days} Days)`;
    if (subtitleEl) {
        subtitleEl.innerHTML = `Archetype: <strong style="color: #38bdf8;" id="itineraryStyleDisplay">${escapeReviewText(effStyle)}</strong> • Budget: <strong style="color: #818cf8;" id="itineraryBudgetDisplay">${escapeReviewText(effBudget)}</strong> (~${estCost})`;
    }
    timelineEl.innerHTML = buildDaysTimelineHtml(daysList);
    if (engineBadgeEl) {
        engineBadgeEl.textContent = '⚡ TravelMate AI Ready';
    }

    syncPlannerCardHeights();
};

window.loadSamplePreset = function(dest, days, style, budget) {
    const destSelect = document.getElementById('plannerDestination');
    if (destSelect) {
        for (let i = 0; i < destSelect.options.length; i++) {
            const optVal = destSelect.options[i].value || '';
            if (optVal === dest || optVal.includes(dest.split(',')[0])) {
                destSelect.selectedIndex = i;
                break;
            }
        }
    }

    const durationInput = document.getElementById('plannerDuration');
    const durationValDisplay = document.getElementById('durationValueDisplay');
    if (durationInput) {
        durationInput.value = days;
        if (durationValDisplay) durationValDisplay.textContent = `${days} Days`;
    }

    document.querySelectorAll('.select-style-card').forEach(c => {
        if ((c.getAttribute('data-style') || '').toLowerCase() === (style || '').toLowerCase()) {
            c.classList.add('active');
        } else {
            c.classList.remove('active');
        }
    });

    document.querySelectorAll('.select-budget-card').forEach(c => {
        if ((c.getAttribute('data-budget') || '').toLowerCase() === (budget || '').toLowerCase()) {
            c.classList.add('active');
        } else {
            c.classList.remove('active');
        }
    });

    window.renderDummyItinerary(dest, days, style, budget);
};

window.updatePreviewForDestination = function(destName) {
    if (!destName) return;
    if (window.hasPlanBeenGenerated && typeof triggerPlannerParamChange === 'function') {
        triggerPlannerParamChange('destination', destName);
    }
};

window.triggerLiveAIGeneration = function() {
    if (typeof triggerPlannerParamChange === 'function') {
        triggerPlannerParamChange('regenerate', null);
    } else {
        const form = document.getElementById('aiPlannerForm');
        if (form && form.requestSubmit) form.requestSubmit();
    }
};

function renderItineraryError(destination, days, errorMsg) {
    renderFallbackItinerary(destination, days, 'Adventure', 'Moderate');
}

function syncPlannerCardHeights() {
    const formCard = document.querySelector('.planner-form-card');
    const outputCard = document.getElementById('itineraryOutput');
    if (!formCard || !outputCard) return;

    if (window.innerWidth > 860) {
        const formHeight = Math.round(formCard.getBoundingClientRect().height || formCard.offsetHeight);
        if (formHeight > 250) {
            outputCard.style.height = `${formHeight}px`;
            outputCard.style.maxHeight = `${formHeight}px`;
            outputCard.style.minHeight = `${formHeight}px`;
        }
    } else {
        outputCard.style.height = '620px';
        outputCard.style.maxHeight = '720px';
        outputCard.style.minHeight = '420px';
    }
}

window.syncPlannerCardHeights = syncPlannerCardHeights;
window.addEventListener('resize', syncPlannerCardHeights);
window.addEventListener('load', syncPlannerCardHeights);

document.addEventListener('DOMContentLoaded', () => {
    const formCard = document.querySelector('.planner-form-card');
    if (formCard && typeof ResizeObserver !== 'undefined') {
        const ro = new ResizeObserver(() => {
            syncPlannerCardHeights();
        });
        ro.observe(formCard);
    }
    syncPlannerCardHeights();
});


window.saveItinerary = function(dest) {
    showToast(`✅ Itinerary for ${dest} saved to your TravelMate profile!`);
    if (typeof window.logUserTelemetry === 'function') {
        window.logUserTelemetry('SAVE_ITINERARY', `Saved itinerary for ${dest}`, { destination: dest });
    }
};

window.handleExportPDF = function(destination, days) {
    if (typeof window.logUserTelemetry === 'function') {
        window.logUserTelemetry('EXPORT_PDF', `Exported/Printed PDF dossier for ${destination} (${days} Days)`, { destination: destination, days: days });
    }
    window.print();
};

/* =========================================
   4. AUTHENTICATION TAB SWITCHER
========================================= */
function initAuthTabs() {
    const tabBtns = document.querySelectorAll('.auth-tab-btn');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const authHeaderTitle = document.getElementById('authHeaderTitle');
    const authHeaderSubtitle = document.getElementById('authHeaderSubtitle');

    if (!tabBtns.length || !loginForm || !registerForm) return;

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const tab = btn.getAttribute('data-tab');
            if (tab === 'register') {
                loginForm.classList.remove('active');
                registerForm.classList.add('active');
                if (authHeaderTitle) authHeaderTitle.textContent = 'Create an Account';
                if (authHeaderSubtitle) authHeaderSubtitle.textContent = 'Join TravelMate AI to unlock personalized smart journeys';
            } else {
                registerForm.classList.remove('active');
                loginForm.classList.add('active');
                if (authHeaderTitle) authHeaderTitle.textContent = 'Welcome Back';
                if (authHeaderSubtitle) authHeaderSubtitle.textContent = 'Access your AI itineraries and saved travel preferences';
            }
        });
    });

    // Real form submission with session persistence and backend authentication
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const emailInput = document.getElementById('loginEmail');
        const passwordInput = document.getElementById('loginPassword');
        const email = emailInput ? emailInput.value.trim() : '';
        const password = passwordInput ? passwordInput.value : '';

        try {
            const resp = await fetch('/api/auth/login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, password: password })
            });
            const data = await resp.json();
            if (data.success) {
                const username = data.user.username;
                const userData = {
                    name: data.user.name,
                    username: username,
                    email: data.user.email,
                    avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80',
                    authProvider: 'Email Cipher',
                    loginTime: new Date().toISOString()
                };
                localStorage.setItem('tm_user', JSON.stringify(userData));
                showToast(`🚀 Authenticated as @${username}! Welcome back.`);
                
                const targetUrl = data.redirect_url || '/home/';

                setTimeout(() => {
                    window.location.href = targetUrl;
                }, 600);
            } else {
                showToast(`❌ ${data.message || 'Login failed'}`);
            }
        } catch (err) {
            console.error('Login error:', err);
            showToast('⚠️ Error connecting to server. Please try again.');
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const emailInput = document.getElementById('regEmail');
        const nameInput = document.getElementById('regName');
        const passwordInput = document.getElementById('regPassword');
        const email = emailInput ? emailInput.value.trim() : '';
        const name = nameInput ? nameInput.value.trim() : '';
        const password = passwordInput ? passwordInput.value : '';

        try {
            const resp = await fetch('/api/auth/register/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, name: name, password: password })
            });
            const data = await resp.json();
            if (data.success) {
                const username = data.user.username;
                const userData = {
                    name: data.user.name,
                    username: username,
                    email: data.user.email,
                    avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&q=80',
                    authProvider: 'Nomad Registration',
                    loginTime: new Date().toISOString()
                };
                localStorage.setItem('tm_user', JSON.stringify(userData));
                showToast(`✨ Account registered for @${username}!`);

                const targetUrl = data.redirect_url || '/home/';

                setTimeout(() => {
                    window.location.href = targetUrl;
                }, 600);
            } else {
                showToast(`❌ ${data.message || 'Registration failed'}`);
            }
        } catch (err) {
            console.error('Registration error:', err);
            showToast('⚠️ Error connecting to server. Please try again.');
        }
    });
}




/* =========================================
   4b. CLIENT TELEMETRY & USER ACTIVITY RECORDER
========================================= */
window.logUserTelemetry = function(actionType, description, metadata) {
    try {
        fetch('/api/activity/log/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action_type: actionType,
                description: description,
                metadata: metadata || {}
            })
        }).catch(() => {});
    } catch (e) {}
};

/* =========================================
   5. TOAST NOTIFICATION UTILITY
========================================= */
function showToast(message) {
    let toast = document.getElementById('globalToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'globalToast';
        toast.className = 'toast-alert';
        document.body.appendChild(toast);
    }

    toast.innerHTML = `<span>${message}</span>`;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
}

/* =========================================
   6. AI CHATBOT FOR FAQ & TRAVEL INQUIRIES
========================================= */
function initAIChatbot() {
    const chatbotCard = document.querySelector('.chatbot-card');
    if (!chatbotCard) return;

    const messagesContainer = document.getElementById('chatbotMessages');
    const inputForm = document.getElementById('chatbotForm');
    const inputField = document.getElementById('chatbotInput');
    const quickChips = document.querySelectorAll('.chat-chip');
    const resetBtn = document.getElementById('resetChatBtn');
    const typingIndicator = document.getElementById('chatTypingIndicator');

    // FAQ Knowledge Base with keyword matcher
    const faqKnowledgeBase = [
        {
            keywords: ['itinerary', 'generate', 'plan', 'create', 'works', 'how it works', 'how does', 'algorithm', 'schedule'],
            header: 'Autonomous Neural Synthesis',
            answer: `
                <p><strong>TravelMate AI</strong> generates personalized itineraries by synthesizing several real-time data inputs:</p>
                <ul>
                    <li>🎯 <strong>Your Archetype & Pacing:</strong> Whether you choose <em>Adventure</em>, <em>Romantic</em>, <em>Cultural</em>, or <em>Relaxed</em>.</li>
                    <li>🌦️ <strong>Meteorological Indices:</strong> Real-time weather patterns sequence outdoor excursions for optimal conditions.</li>
                    <li>👥 <strong>Crowd Density Forecasts:</strong> Routes are timed to visit popular landmarks during off-peak hours.</li>
                    <li>💎 <strong>Curated Hidden Gems:</strong> High-density local artisan stalls and secret viewpoints are woven directly into your schedule.</li>
                </ul>
                <a href="/planner/" class="msg-action-btn">Launch AI Trip Planner ✨</a>
            `
        },
        {
            keywords: ['offline', 'cellular', 'internet', 'wifi', 'without internet', 'data', 'roaming', 'download'],
            header: 'Offline Vector Architecture',
            answer: `
                <p><strong>Yes, TravelMate AI functions completely offline!</strong> 📶</p>
                <ul>
                    <li>🗺️ <strong>Offline Vector Caching:</strong> Once an itinerary is synthesized, high-resolution vector maps and landmark notes are stored locally on your device.</li>
                    <li>📍 <strong>GPS Without Data:</strong> Device GPS coordinates sync with your cached maps without requiring expensive roaming packages.</li>
                    <li>📑 <strong>Zero-Lag Navigation:</strong> Daily timelines and packing checklists remain fully accessible in remote alpine valleys or island shores.</li>
                </ul>
            `
        },
        {
            keywords: ['budget', 'cost', 'price', 'estimate', 'optimize', 'money', 'expensive', 'dollar', 'euro'],
            header: 'Neural Budget Telemetry',
            answer: `
                <p><strong>How we calculate & optimize your travel budget:</strong> 💰</p>
                <ul>
                    <li>🪙 <strong>Nomad / Budget (~₹3,500/day):</strong> Prioritizes boutique hostels, rail transit passes, street food gastronomy, and free cultural monuments.</li>
                    <li>💳 <strong>Moderate / Comfort (~₹7,500/day):</strong> Includes 4-star glass suites, private transit transfers, guided museum passes, and rooftop dining.</li>
                    <li>💎 <strong>Luxury (~₹16,000+/day):</strong> 5-star royal heritage palaces, private culinary masterclasses, chartered boats, and bespoke tours.</li>
                </ul>
                <p>Our algorithms calculate dynamic Indian Rupee (₹ INR) telemetry across any itinerary duration!</p>
            `
        },
        {
            keywords: ['export', 'print', 'pdf', 'save', 'share', 'download plan'],
            header: 'Export & Archival Telemetry',
            answer: `
                <p><strong>Absolutely! You have multiple ways to keep your itineraries:</strong> 📄</p>
                <ul>
                    <li>💾 <strong>Save to Cloud Profile:</strong> Keep unlimited trips in your traveler profile for instant retrieval across all your devices.</li>
                    <li>🖨️ <strong>Print-Ready PDF:</strong> Generate clean, beautifully formatted vector PDF dossiers with one click from the AI Planner.</li>
                    <li>🔗 <strong>Companion Share:</strong> Generate direct shareable links to collaborate with fellow travelers.</li>
                </ul>
                <a href="/planner/" class="msg-action-btn">Try It in AI Planner →</a>
            `
        },
        {
            keywords: ['free', 'cost to use', 'pricing', 'subscription', 'paid', 'tier'],
            header: 'Transparent Pricing Model',
            answer: `
                <p><strong>TravelMate AI is 100% Free for Core Operations!</strong> 💎</p>
                <ul>
                    <li>✅ <strong>Unlimited Itinerary Generation:</strong> Synthesize schedules for any Indian coordinate with zero fees.</li>
                    <li>✅ <strong>Indian Destination Directory:</strong> Full filtering across beaches, mountains, heritage, and adventure coordinates.</li>
                    <li>✅ <strong>Offline PDF Printing:</strong> Free document generation.</li>
                    <li>🌟 <strong>Optional Nomad Cloud:</strong> Sign in with Google to save trips to your personal dashboard and unlock automated route synchronization.</li>
                </ul>
            `
        },
        {
            keywords: ['destination', 'recommend', 'where to go', 'popular', 'trending', 'places', 'beach', 'mountain', 'heritage', 'adventure'],
            header: 'Curated Indian Coordinate Suggestions',
            answer: `
                <p><strong>Top trending famous Indian coordinates for this season:</strong> 🇮🇳</p>
                <ul>
                    <li>🏖️ <strong>Goa Coastline:</strong> Golden sands, palm shacks, water sports, and Portuguese architecture.</li>
                    <li>🏔️ <strong>Manali & Rohtang Pass:</strong> Snow-capped Himalayan passes, pine cedar valleys, and Solang paragliding.</li>
                    <li>🏰 <strong>Jaipur, Rajasthan:</strong> Pink sandstone fortresses, royal Amer Fort, and Johari Bazaar.</li>
                    <li>⛵ <strong>Udaipur, Rajasthan:</strong> Majestic City Palace, serene Lake Pichola boat cruises, and luxury havelis.</li>
                    <li>🕉️ <strong>Varanasi Ghats:</strong> Evening Ganga Aarti, ancient spiritual ghats, and silk weaving quarters.</li>
                    <li>🌿 <strong>Munnar, Kerala:</strong> Misty emerald tea plantations, cascading waterfalls, and backwater retreats.</li>
                </ul>
                <a href="/explore/" class="msg-action-btn">Browse Full Directory →</a>
            `
        },
        {
            keywords: ['packing', 'pack', 'luggage', 'clothes', 'what to bring', 'baggage'],
            header: 'Smart Packing Assistant',
            answer: `
                <p><strong>Algorithmic Packing Recommendations:</strong> 🎒</p>
                <ul>
                    <li>🏖️ <strong>For Coastal/Beaches (Goa):</strong> Reef-safe SPF 50 sunscreen, polarized sunglasses, quick-dry linen shirts, water shoes, and dry-bag.</li>
                    <li>🏔️ <strong>For Alpine/Mountains (Manali):</strong> Layered thermal fleece, windproof jacket, mountain UV shades, sturdy trekking shoes, and power bank.</li>
                    <li>🏛️ <strong>For Cultural/Heritage (Jaipur/Varanasi):</strong> Breathable cotton clothing, modest temple wear, comfortable walking shoes, and hydration flask.</li>
                </ul>
            `
        },
        {
            keywords: ['login', 'google', 'auth', 'account', 'sign in', 'security', 'privacy'],
            header: 'Zero-Knowledge Security',
            answer: `
                <p><strong>Secure Traveler Authentication:</strong> 🔒</p>
                <ul>
                    <li>⚡ <strong>One-Tap Google Sign-In:</strong> Instantly authenticate via Google Identity Services without remembering passwords.</li>
                    <li>🛡️ <strong>Zero-Knowledge Encryption:</strong> Your saved routes, budget notes, and preferences are encrypted client-side.</li>
                    <li>🔄 <strong>Instant Synchronization:</strong> Access your customized trips on your laptop, tablet, or phone seamlessly.</li>
                </ul>
                <a href="/auth/" class="msg-action-btn">Sign In to Traveler Portal →</a>
            `
        },
        {
            keywords: ['hello', 'hi', 'hey', 'greetings', 'who are you', 'what can you do'],
            header: 'Neural Assistant Synchronized',
            answer: `
                <p>Hello explorer! 👋 I'm your <strong>TravelMate Neural Concierge</strong>.</p>
                <p>I can help you with:</p>
                <ul>
                    <li>✨ Explaining how our AI designs dynamic trip timelines</li>
                    <li>📶 Guiding you through offline navigation & maps</li>
                    <li>💰 Estimating budgets for backpacking, moderate, or luxury travel in ₹ INR</li>
                    <li>🇮🇳 Recommending handpicked famous Indian destinations</li>
                    <li>🎒 Providing custom packing checklists</li>
                </ul>
                <p><em>What would you like to explore today?</em></p>
            `
        },
        {
            keywords: ['thank', 'thanks', 'awesome', 'great', 'cool', 'helpful'],
            header: 'Always At Your Service',
            answer: `
                <p>You're very welcome! 🚀 Safe travels wherever your coordinates take you. Feel free to ask more questions anytime or synthesize a fresh itinerary in the <strong>AI Planner</strong>!</p>
                <a href="/planner/" class="msg-action-btn">Synthesize New Plan ✨</a>
            `
        }
    ];

    // Response generator
    function generateBotResponse(userQuery) {
        const query = userQuery.toLowerCase().trim();
        
        // Check for matching keywords in knowledge base
        let bestMatch = null;
        let maxMatches = 0;

        for (const item of faqKnowledgeBase) {
            let matchCount = 0;
            for (const kw of item.keywords) {
                if (query.includes(kw)) {
                    matchCount++;
                }
            }
            if (matchCount > maxMatches) {
                maxMatches = matchCount;
                bestMatch = item;
            }
        }

        if (bestMatch && maxMatches > 0) {
            return {
                header: bestMatch.header,
                html: bestMatch.answer
            };
        }

        // Contextual smart fallback
        return {
            header: 'TravelMate Intelligence',
            html: `
                <p>I understand you're inquiring about <em>"${escapeHtml(userQuery)}"</em>.</p>
                <p>TravelMate AI is designed to make global exploration seamless. You can:</p>
                <ul>
                    <li>🚀 <strong>Plan an Itinerary:</strong> Use our AI Planner to generate custom schedules from 1 to 14 days.</li>
                    <li>🔍 <strong>Explore Destinations:</strong> Browse beaches, mountains, heritage cities, and adventure hotspots.</li>
                    <li>📶 <strong>Go Offline:</strong> Access your travel timelines without an active cellular connection.</li>
                </ul>
                <p>Try asking about: <em>"How does it work offline?"</em>, <em>"How are budgets calculated?"</em>, or <em>"What are the best destinations?"</em></p>
                <a href="/planner/" class="msg-action-btn">Launch AI Trip Planner ✨</a>
            `
        };
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatMarkdownToHtml(rawText) {
        if (!rawText) return '';
        let html = escapeHtml(rawText);

        // Convert bold: **text** -> <strong>text</strong>
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Convert italic: *text* -> <em>$1</em>
        html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
        
        // Convert bullet points: * or - at start of line
        const lines = html.split('\n');
        let inList = false;
        let formattedLines = [];

        for (let line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
                if (!inList) {
                    formattedLines.push('<ul style="margin: 0.4rem 0 0.6rem 0; padding-left: 1.2rem; line-height: 1.55;">');
                    inList = true;
                }
                const itemContent = trimmed.replace(/^[-*•]\s+/, '');
                formattedLines.push(`<li>${itemContent}</li>`);
            } else {
                if (inList) {
                    formattedLines.push('</ul>');
                    inList = false;
                }
                if (trimmed.startsWith('### ')) {
                    formattedLines.push(`<h5 style="margin: 0.6rem 0 0.3rem 0; color: #38bdf8;">${trimmed.substring(4)}</h5>`);
                } else if (trimmed.startsWith('## ')) {
                    formattedLines.push(`<h4 style="margin: 0.7rem 0 0.35rem 0; color: #00f2fe;">${trimmed.substring(3)}</h4>`);
                } else if (trimmed.length > 0) {
                    formattedLines.push(`<p style="margin: 0.35rem 0;">${trimmed}</p>`);
                }
            }
        }
        if (inList) {
            formattedLines.push('</ul>');
        }

        return formattedLines.join('');
    }

    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message user-message';
        msgDiv.innerHTML = `
            <div class="msg-avatar">👤</div>
            <div class="msg-bubble">
                <p>${escapeHtml(text)}</p>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function appendBotMessage(header, contentHtml) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message bot-message';
        msgDiv.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="msg-bubble">
                <div class="msg-header">${header}</div>
                ${contentHtml}
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function handleUserInput(text) {
        const trimmed = text.trim();
        if (!trimmed) return;

        // Append user message
        appendUserMessage(trimmed);

        // Show typing indicator
        if (typingIndicator) {
            typingIndicator.style.display = 'flex';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        try {
            const resp = await fetch('/api/ai/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: trimmed })
            });
            const data = await resp.json();

            if (typingIndicator) {
                typingIndicator.style.display = 'none';
            }

            if (data && data.success && data.reply) {
                const formatted = formatMarkdownToHtml(data.reply);
                appendBotMessage('TravelMate Neural Concierge (Gemini 3.8 Flash)', formatted);
                return;
            }
        } catch (fetchErr) {
            console.warn('Backend Gemini chat API error, falling back to local knowledge base:', fetchErr);
        }

        if (typingIndicator) {
            typingIndicator.style.display = 'none';
        }
        const fallback = generateBotResponse(trimmed);
        appendBotMessage(fallback.header, fallback.html);
    }

    // Form submit
    inputForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = inputField.value;
        if (!text.trim()) return;
        inputField.value = '';
        handleUserInput(text);
    });

    // Quick chip buttons
    quickChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const question = chip.getAttribute('data-question') || chip.textContent;
            handleUserInput(question);
        });
    });

    // Reset button
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            messagesContainer.innerHTML = `
                <div class="chat-message bot-message">
                    <div class="msg-avatar">🤖</div>
                    <div class="msg-bubble">
                        <div class="msg-header">TravelMate AI • Concierge</div>
                        <p>🔄 Conversation refreshed! How can I assist your travel journeys or clarify platform features today?</p>
                        <p class="msg-hint">💡 <em>Click any quick chip above or type your question below.</em></p>
                    </div>
                </div>
            `;
            showToast('🔄 Chat session refreshed.');
        });
    }
}

/* =========================================
   7. GLOBAL AI CHATBOT POPUP MODAL CONTROLS
========================================= */
window.openAIChatbotModal = function() {
    const overlay = document.getElementById('aiChatbotModalOverlay');
    if (overlay) {
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden'; // Lock background scrolling
        if (typeof window.logUserTelemetry === 'function') {
            window.logUserTelemetry('OPEN_CHATBOT', 'Opened AI Neural Concierge modal');
        }
        setTimeout(() => {
            const input = document.getElementById('chatbotInput');
            if (input) input.focus();
        }, 150);
    }
};

window.closeAIChatbotModal = function() {
    const overlay = document.getElementById('aiChatbotModalOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = ''; // Restore background scrolling
    }
};

window.handleChatbotOverlayClick = function(e) {
    if (e.target.id === 'aiChatbotModalOverlay') {
        closeAIChatbotModal();
    }
};

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAIChatbotModal();
    }
});

/* =========================================
   8. GOOGLE AUTHENTICATION & LANDING PORTAL
========================================= */
window.openLandingPortal = function() {
    window.location.href = '/auth/';
};

window.closeLandingPortal = function() {
    const modal = document.getElementById('landingPortalModal');
    if (modal) {
        modal.classList.remove('active');
    }
};

window.triggerGoogleAuth = function() {
    const allauthForm = document.querySelector('form[action*="google"]');
    if (allauthForm) {
        allauthForm.submit();
        return;
    }
    window.location.href = '/accounts/google/login/';
};

window.closeGoogleAuth = function() {
    // No-op for backward compatibility
};

window.completeGoogleAuth = function(name, email, avatar) {
    const emailStr = email || 'alex.rivera.travel@gmail.com';
    const username = emailStr.split('@')[0];
    const userData = {
        name: name || 'Alex Rivera',
        username: username,
        email: emailStr,
        avatar: avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80',
        authProvider: 'Google OAuth 2.0',
        loginTime: new Date().toISOString()
    };

    localStorage.setItem('tm_user', JSON.stringify(userData));
    closeGoogleAuth();
    closeLandingPortal();

    showToast(`✨ Google Verified: Welcome, @${userData.username}!`);

    // Refresh live review section identity if present
    if (typeof window.refreshReviewIdentity === 'function') {
        window.refreshReviewIdentity();
    }

    const currentPath = window.location.pathname.replace(/\/+$/, '') || '/';
    if (currentPath === '' || currentPath === '/' || currentPath === '/auth') {
        setTimeout(() => {
            window.location.href = '/home/';
        }, 800);
    }
};

window.handleQuickLogin = async function(e) {
    if (e) e.preventDefault();
    const emailInput = document.getElementById('quickEmail');
    const passwordInput = document.getElementById('quickPassword');
    const email = emailInput ? emailInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value : '';

    try {
        const resp = await fetch('/api/auth/login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, password: password })
        });
        const data = await resp.json();
        if (data.success) {
            const username = data.user.username;
            const userData = {
                name: data.user.name,
                username: username,
                email: data.user.email,
                avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80',
                authProvider: 'Email Cipher',
                loginTime: new Date().toISOString()
            };

            localStorage.setItem('tm_user', JSON.stringify(userData));
            closeLandingPortal();
            showToast(`🚀 Authenticated as @${userData.username}! Entering TravelMate AI...`);

            setTimeout(() => {
                window.location.href = data.redirect_url || '/home/';
            }, 600);
        } else {
            showToast(`❌ ${data.message || 'Login verification failed'}`);
        }
    } catch (err) {
        console.error('Quick login error:', err);
        showToast('⚠️ Error connecting to server. Please try again.');
    }
};

window.signOutUser = function() {
    localStorage.removeItem('tm_user');
    window.location.href = '/accounts/logout/';
};

/* =========================================
   9. INTERACTIVE REVIEW SUBMISSION & WALL FEATURE
========================================= */
function initReviewSection() {
    const reviewForm = document.getElementById('reviewSubmissionForm');
    const reviewGrid = document.getElementById('testimonialsGrid');
    if (!reviewForm || !reviewGrid) return;

    const starBtns = document.querySelectorAll('#interactiveStars .star-btn');
    const ratingFeedback = document.getElementById('ratingFeedbackText');
    const roleChips = document.querySelectorAll('#roleChipsList .role-chip');
    const textArea = document.getElementById('reviewTextInput');
    const charCount = document.getElementById('reviewCharCount');

    let currentRating = 5;
    let currentRole = 'Solo Backcountry Adventurer';

    const ratingDescriptions = {
        1: '1.0 / 5.0 (Disappointing Voyage)',
        2: '2.0 / 5.0 (Average Trip)',
        3: '3.0 / 5.0 (Good Expedition)',
        4: '4.0 / 5.0 (Great Adventure)',
        5: '5.0 / 5.0 (Exceptional Odyssey)'
    };

    // 1. Get Logged-In User from Session (Automatic)
    function getActiveUser() {
        const savedUser = localStorage.getItem('tm_user');
        if (savedUser) {
            try {
                const user = JSON.parse(savedUser);
                const email = user.email || 'elena.rostova@gmail.com';
                const username = user.username || email.split('@')[0];
                return {
                    name: user.name || username,
                    username: username,
                    email: email,
                    avatar: user.avatar || 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=120&q=80',
                    authProvider: user.authProvider || 'Verified Nomad'
                };
            } catch (e) {}
        }
        // Default traveler profile if not set in localStorage
        return {
            name: 'Nomad Traveler',
            username: 'traveler',
            email: 'traveler@travelmate.ai',
            avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=120&q=80',
            authProvider: 'Verified Account'
        };
    }

    // 2. Render Reviewer Identity Badge (Display-only, no login controls)
    function renderReviewerBadge() {
        const user = getActiveUser();
        const avatarEl = document.getElementById('reviewerBadgeAvatar');
        const usernameEl = document.getElementById('reviewerBadgeUsername');
        const noteUsernameEl = document.getElementById('submitNoteUsername');

        if (avatarEl) {
            avatarEl.src = user.avatar;
            avatarEl.alt = user.name || user.username;
        }
        if (usernameEl) {
            usernameEl.textContent = user.name || user.username;
        }
        if (noteUsernameEl) {
            noteUsernameEl.textContent = user.name || user.username;
        }
    }

    window.refreshReviewIdentity = function() {
        renderReviewerBadge();
    };

    // 3. Interactive Star Rating
    starBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const ratingVal = parseInt(btn.getAttribute('data-rating'), 10) || 5;
            currentRating = ratingVal;
            highlightStars(ratingVal);
        });

        btn.addEventListener('mouseenter', () => {
            const hoverVal = parseInt(btn.getAttribute('data-rating'), 10) || 5;
            highlightStars(hoverVal);
        });
    });

    const starContainer = document.getElementById('interactiveStars');
    if (starContainer) {
        starContainer.addEventListener('mouseleave', () => {
            highlightStars(currentRating);
        });
    }

    function highlightStars(val) {
        starBtns.forEach(btn => {
            const btnVal = parseInt(btn.getAttribute('data-rating'), 10);
            if (btnVal <= val) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        if (ratingFeedback) {
            ratingFeedback.textContent = ratingDescriptions[val] || `${val}.0 / 5.0`;
        }
    }

    // 4. Role Selection Chips
    roleChips.forEach(chip => {
        chip.addEventListener('click', () => {
            roleChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentRole = chip.getAttribute('data-role') || chip.textContent;
        });
    });

    // 5. Textarea Character Counter
    if (textArea && charCount) {
        textArea.addEventListener('input', () => {
            const length = textArea.value.length;
            charCount.textContent = `${length} / 400`;
            if (length > 350) {
                charCount.style.color = '#ec4899';
            } else {
                charCount.style.color = '#94a3b8';
            }
        });
    }

    // 6. Render Custom Featured Reviews on the Wall
    function renderCustomReviews() {
        const existingCustomCards = reviewGrid.querySelectorAll('.featured-review-card');
        existingCustomCards.forEach(card => card.remove());

        const rawReviews = localStorage.getItem('tm_custom_reviews');
        let reviews = [];
        if (rawReviews) {
            try {
                reviews = JSON.parse(rawReviews);
            } catch (e) {
                reviews = [];
            }
        }

        reviews.forEach(review => {
            const card = document.createElement('div');
            card.className = 'testimonial-card featured-review-card';
            card.id = review.id;

            const starsHtml = '★'.repeat(review.rating || 5) + '☆'.repeat(Math.max(0, 5 - (review.rating || 5)));

            card.innerHTML = `
                <div class="featured-card-top">
                    <span class="featured-badge-pill">★ FEATURED NOMAD REVIEW</span>
                    <span class="featured-live-pill">Verified ${review.name || review.username}</span>
                </div>
                <div>
                    <div class="testimonial-stars">${starsHtml}</div>
                    <p class="testimonial-quote">"${escapeReviewText(review.quote)}"</p>
                </div>
                <div class="testimonial-author-wrapper">
                    <img src="${review.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80'}" alt="${review.name || review.username}" class="testimonial-avatar verified-avatar">
                    <div class="testimonial-author-info">
                        <h4>${review.name || review.username} <span class="verified-badge-check" title="Verified Login Email">✓</span></h4>
                        <p>${review.email} • ${review.role}</p>
                    </div>
                    <button type="button" class="btn-delete-review" onclick="deleteCustomReview('${review.id}')" title="Remove this review">✕</button>
                </div>
            `;

            // Prepend at the beginning of the grid
            reviewGrid.insertBefore(card, reviewGrid.firstChild);
        });
    }

    function escapeReviewText(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 7. Form Submission Handler
    reviewForm.addEventListener('submit', (e) => {
        // If action points to Django backend add_review, allow standard POST submission!
        const actionUrl = reviewForm.getAttribute('action');
        if (actionUrl && actionUrl.includes('/add-review/')) {
            const comment = textArea ? textArea.value.trim() : '';
            if (!comment || comment.length < 5) {
                e.preventDefault();
                showToast('⚠️ Please write at least 5 characters for your review.');
                return;
            }
            const ratingInput = document.getElementById('reviewRatingInput');
            if (ratingInput) ratingInput.value = currentRating;
            return; // Let browser submit directly to Django add_review view!
        }

        e.preventDefault();

        const quote = textArea ? textArea.value.trim() : '';
        if (!quote || quote.length < 8) {
            showToast('⚠️ Please write at least 8 characters describing your travel experience.');
            return;
        }

        // Get identity automatically from login
        const user = getActiveUser();
        const username = user.username;
        const email = user.email;

        const newReview = {
            id: 'rev_' + Date.now(),
            username: username, // Extracted username from login email!
            email: email,
            avatar: user.avatar,
            role: currentRole,
            rating: currentRating,
            quote: quote,
            createdAt: new Date().toISOString()
        };

        // Save to localStorage
        let reviews = [];
        try {
            reviews = JSON.parse(localStorage.getItem('tm_custom_reviews') || '[]');
        } catch (e) {
            reviews = [];
        }
        reviews.unshift(newReview);
        localStorage.setItem('tm_custom_reviews', JSON.stringify(reviews));

        // Re-render
        renderCustomReviews();

        // Reset form inputs
        textArea.value = '';
        if (charCount) charCount.textContent = '0 / 400';

        // Feedback & smooth scroll
        showToast(`🎉 Review featured on Nomad Wall under username @${username}!`);

        const createdCard = document.getElementById(newReview.id);
        if (createdCard) {
            createdCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });

    // Global delete handler
    window.deleteCustomReview = function(id) {
        let reviews = [];
        try {
            reviews = JSON.parse(localStorage.getItem('tm_custom_reviews') || '[]');
        } catch (e) {}

        reviews = reviews.filter(r => r.id !== id);
        localStorage.setItem('tm_custom_reviews', JSON.stringify(reviews));
        renderCustomReviews();
        showToast('🗑️ Review removed from the Nomad Wall.');
    };

    // Initial setup
    renderReviewerBadge();
    renderCustomReviews();
}
