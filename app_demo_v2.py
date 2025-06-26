import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from shiny import App, ui, render, reactive
import os
import base64
from uuid import uuid4

# Bank configuration - Sales demo version
BANK_CONFIG = {
    "beobk2nv6z": {
        "name": "Beobank",
        "file": "data/beobank_b2_accessibility_final.xlsx",
        "color_primary": "#1e3a8a",
        "color_secondary": "#3b82f6",
        "logo_path": "logos/beobank-logo.webp"
    },
    "ingb4mb7q0": {
        "name": "ING",
        "file": "data/ing_b2_final_results.xlsx", 
        "color_primary": "#ff6200",
        "color_secondary": "#ff8533",
        "logo_path": "logos/ing-logo.png"
    },
    "blfsq9k1w8": {
        "name": "Belfius",
        "file": "data/belfius_b2_accessibility_final.xlsx",
        "color_primary": "#8B1538", 
        "color_secondary": "#C41E3A",
        "logo_path": "logos/belfius-logo.png"
    },
    "argnt4x7m2": {
        "name": "Argenta",
        "file": "data/argenta_b2_accessibility_scores.xlsx",
        "color_primary": "#00A651", 
        "color_secondary": "#7CB342",
        "logo_path": "logos/argenta-logo.png"
    },
    "kytrd5cz9n": {
        "name": "Keytrade",
        "file": "data/keytrade_b2_accessibility_scores.xlsx",
        "color_primary": "#2E3192", 
        "color_secondary": "#5C6BC0",
        "logo_path": "logos/keytrade-logo.png"
    },
    "crln9xs3p1": {
        "name": "Crelan",
        "file": "data/crelan_b2_final_results.xlsx",
        "color_primary": "#E30613", 
        "color_secondary": "#FF5722",
        "logo_path": "logos/crelan-logo.jpg"
    },
    "bnppf8td4e": {
        "name": "BNP Paribas Fortis",
        "file": "data/bnp_paribas_fortis_b2_final_results.xlsx",
        "color_primary": "#00A550", 
        "color_secondary": "#006633",
        "logo_path": "logos/bnp-logo.png"
    },
    "kbcx6rj2v4": {
        "name": "KBC",
        "file": "data/kbc_b2_final_results.xlsx",
        "color_primary": "#0079C1", 
        "color_secondary": "#00B5E2",
        "logo_path": "logos/kbc-logo.png"
    }
}

ADMIN_CONFIG = {
    "admin_password": "sailpeak2025admin",  # Change this password
}

def create_copy_button(url):
    """Helper function to create a copy button for URLs"""
    return ui.tags.button(
        "📋",
        onclick=f"navigator.clipboard.writeText('{url}'); this.textContent='✓'; setTimeout(() => this.textContent='📋', 1000);",
        class_="copy-button",
        title="Copy URL"
    )

def get_detailed_insight(example):
    """Generate detailed insights for example pages using rationale data"""
    score = example['Compliance Level']
    page_type = example['Page Type']
    rationale = example.get('Rationale', '')
    
    # Extract key insights from rationale if available
    if rationale and len(rationale) > 50:
        # Parse rationale for key themes
        rationale_lower = rationale.lower()
        
        # Extract vocabulary insights
        vocab_issues = []
        if 'technical terms' in rationale_lower or 'banking terms' in rationale_lower:
            vocab_issues.append("technical terminology")
        if 'abbreviations' in rationale_lower or 'jargon' in rationale_lower:
            vocab_issues.append("specialized abbreviations")
        if 'complex' in rationale_lower and 'vocabulary' in rationale_lower:
            vocab_issues.append("complex vocabulary")
            
        # Extract grammar insights
        grammar_insights = []
        if 'simple' in rationale_lower and ('sentences' in rationale_lower or 'structures' in rationale_lower):
            grammar_insights.append("clear sentence structure")
        if 'complex sentences' in rationale_lower:
            grammar_insights.append("some complex sentences")
        if 'active voice' in rationale_lower:
            grammar_insights.append("good use of active voice")
            
        # Extract clarity insights
        clarity_issues = []
        if 'transitions' in rationale_lower and ('weak' in rationale_lower or 'poor' in rationale_lower):
            clarity_issues.append("weak transitions between sections")
        if 'disjointed' in rationale_lower or 'jumps between' in rationale_lower:
            clarity_issues.append("disjointed content flow")
        if 'clear' in rationale_lower and 'purpose' in rationale_lower:
            clarity_issues.append("clear section purposes")
            
        # Generate specific recommendations based on rationale analysis
        recommendations = []
        
        if vocab_issues:
            recommendations.append(f"Simplify {', '.join(vocab_issues)} for better accessibility")
        if 'complex sentences' in rationale_lower:
            recommendations.append("Break down complex sentences into shorter, clearer statements")
        if clarity_issues and any('weak' in issue or 'disjointed' in issue for issue in clarity_issues):
            recommendations.append("Improve content organization and add clearer transitions")
        if 'coherence' in rationale_lower and ('weak' in rationale_lower or 'poor' in rationale_lower):
            recommendations.append("Strengthen logical flow between content sections")
            
        # Provide score-based context
        if score >= 80:
            base_message = f"This {page_type.lower()} page demonstrates strong B2 accessibility."
        elif score >= 70:
            base_message = f"This {page_type.lower()} page meets B2 standards with room for improvement."
        else:
            base_message = f"This {page_type.lower()} page needs significant accessibility improvements."
            
        if recommendations:
            return f"{base_message} Key areas for enhancement: {'; '.join(recommendations[:2])}."
        else:
            return f"{base_message} The content analysis suggests focusing on vocabulary simplification and content structure."
    
    # Fallback to score-based insights if no rationale available
    if score >= 80:
        return f"This {page_type.lower()} page demonstrates excellent B2 accessibility compliance. The content structure and language complexity are well-optimized for cognitive accessibility. Consider using this page as a template for other {page_type.lower()} content."
    elif score >= 70:
        return f"This {page_type.lower()} page meets B2 standards but has room for improvement. Focus on simplifying complex sentences and reducing cognitive load through better information hierarchy."
    elif score >= 60:
        return f"This {page_type.lower()} page shows moderate accessibility issues. Key improvements needed: simplify vocabulary, break down complex information, and improve content structure."
    else:
        return f"This {page_type.lower()} page requires significant accessibility improvements. Priority actions: comprehensive content rewrite focusing on plain language and reduced cognitive complexity."

def calculate_weighted_score(df):
    """Calculate weighted score based on page type importance - results stay as percentages"""
    
    # Define importance weights for different page types
    PAGE_TYPE_WEIGHTS = {
        'Product': 2.5,     # Highest importance - core business
        'Legal': 2.0,       # High importance - regulatory requirements  
        'FAQ': 2.0,         # Important - user support
        'Other': 1.5,       # Medium importance - general content
        'Blog': 1.5,        # Lower importance - marketing content
        'Contact': 1.0      # Baseline - simpler content
    }
    
    # Calculate page type distribution for frequency penalties
    total_pages = len(df)
    page_type_counts = df['Page Type'].value_counts()
    
    # Calculate weighted average (this keeps results as percentages)
    total_weighted_score = 0
    total_weight = 0
    
    # Group by page type and calculate weighted contribution
    for page_type in df['Page Type'].unique():
        type_pages = df[df['Page Type'] == page_type]
        avg_score = type_pages['Compliance Level'].mean()  # This is already a percentage
        page_count = len(type_pages)
        
        # Get importance weight for this page type
        importance_weight = PAGE_TYPE_WEIGHTS.get(page_type, 1.0)
        
        # Apply frequency penalty for over-representation
        frequency = page_count / total_pages
        
        if frequency > 0.5:  # 50%+ penalty
            frequency_penalty = 0.7  # 30% reduction in weight
        elif frequency > 0.4:  # 40%+ penalty  
            frequency_penalty = 0.8  # 20% reduction in weight
        elif frequency > 0.3:  # 30%+ penalty
            frequency_penalty = 0.9  # 10% reduction in weight
        else:
            frequency_penalty = 1.0  # No penalty
        
        # Apply both importance weight and frequency penalty
        final_weight = importance_weight * frequency_penalty
        
        # Add to weighted sum (score stays as percentage, we just weight the contribution)
        total_weighted_score += avg_score * page_count * final_weight
        total_weight += page_count * final_weight
    
    # Return weighted average (still a percentage between 0-100)
    return total_weighted_score / total_weight if total_weight > 0 else 0


# UI Layout
app_ui = ui.page_fluid(
    ui.tags.head(
        # Import Sailpeak fonts
        ui.tags.link(href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap", rel="stylesheet"),
        ui.tags.style("""
                /* CSS Variables - MUST BE FIRST */
                :root {
                    --primary-color: #242D31;
                    --secondary-color: #F7E194;
                    --neutral-dark: #2E363A;
                    --neutral-medium: #36464B;
                    --neutral-light: #8C9091;
                    --background-color: #F2F3EF;
                    --primary-blue: #1f4e79;
                    --secondary-blue: #8b9dc3;
                    --light-blue: rgba(139, 157, 195, 0.2);
                    --success-green: #28a745;
                    --warning-orange: #fd7e14;
                    --danger-red: #dc3545;
                }

                /* Sailpeak Branding Styles */
                body {
                    font-family: 'Inter', sans-serif;
                    background-color: #F2F3EF;
                    color: #242D31;
                    max-width: 100vw;
                    overflow-x: hidden;
                }
                h1, h2, h3, h4, h5 {
                    font-family: 'Inter', sans-serif;
                    font-weight: 600;
                    color: #242D31;
                }

                /* Fixed Professional Header Layout */
                .header-container {
                    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                    border-bottom: 2px solid #e9ecef;
                    padding: 0 !important;
                    margin: 0 !important;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                    display: block !important;
                }

                /* Top bar with logout and Sailpeak logo */
                .top-bar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px 30px;
                    background: #ffffff;
                    border-bottom: 1px solid #e9ecef;
                }

                /* Main header content */
                .main-header {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 25px 30px;
                    gap: 30px;
                    min-height: 100px;
                }

                /* Bank logo styling */
                .bank-logo-section {
                    flex: 0 0 auto;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #ffffff;
                    padding: 20px;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    border: 1px solid #e9ecef;
                }

                .bank-logo {
                    max-height: 70px !important;
                    max-width: 180px !important;
                    object-fit: contain;
                }

                /* Title section */
                .title-section-new {
                    flex: 1;
                    text-align: center;
                    padding: 0 20px;
                }

                .title-header {
                    background: none !important;
                    color: #2c3e50 !important;
                    font-size: 2.5rem !important;
                    font-weight: 700 !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    letter-spacing: -0.5px;
                    line-height: 1.2;
                }

                .title-subtitle {
                    color: #6c757d;
                    font-size: 1.1rem;
                    font-weight: 400;
                    margin-top: 8px;
                    letter-spacing: 0.5px;
                }

                /* Sailpeak logo in top bar */
                .sailpeak-top-bar {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }

                .sailpeak-logo {
                    height: 35px !important;
                    object-fit: contain;
                }

                .sailpeak-text {
                    font-size: 0.9rem;
                    color: #6c757d;
                    font-weight: 500;
                }

                /* Logout button styling */
                .logout-container {
                    margin: 0 !important;
                }

                .logout-btn {
                    background: #6c757d !important;
                    color: white !important;
                    padding: 8px 16px !important;
                    border-radius: 6px !important;
                    font-size: 13px !important;
                    font-weight: 500 !important;
                    border: none;
                    transition: all 0.2s ease;
                }

                .logout-btn:hover {
                    background: #5a6268 !important;
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }

                /* FULL WIDTH KPI CARDS FIX */
                /* FIXED WIDTH KPI CARDS - OVERRIDE INLINE STYLES */
                .kpi-wrapper {
                    background: #ffffff;
                    padding: 30px;
                    margin: 30px 0;
                    border-radius: 16px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                    width: 100%;
                }

                .score-cards-container {
                    display: flex !important;
                    justify-content: space-between !important;
                    gap: 15px !important;
                    width: 100% !important;
                }

                .score-cards-container > div {
                    flex: 1 !important;
                    width: calc(20% - 12px) !important;
                    min-width: unset !important;
                    max-width: unset !important;
                }

                /* Override any inline styles from Python */
                .score-cards-container > div[style] {
                    width: calc(20% - 12px) !important;
                    flex: 1 !important;
                }

                @media (max-width: 767px) {
                    .kpi-wrapper {
                        padding: 20px 15px;
                    }
                    
                    .score-cards-container {
                        overflow-x: auto !important;
                        justify-content: flex-start !important;
                    }
                    
                    .score-cards-container > div,
                    .score-cards-container > div[style] {
                        min-width: 200px !important;
                        width: 200px !important;
                        flex: 0 0 200px !important;
                    }
                }
                /* Individual KPI card styling */
                .kpi-card {
                    background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
                    color: white;
                    padding: 24px;
                    border-radius: 12px;
                    text-align: center;
                    box-shadow: 0 4px 12px rgba(31, 78, 121, 0.2);
                    transition: transform 0.2s ease;
                }

                .kpi-card:hover {
                    transform: translateY(-2px);
                }

                .kpi-value {
                    font-size: 2.5rem;
                    font-weight: bold;
                    margin: 8px 0;
                    line-height: 1;
                }

                .kpi-label {
                    font-size: 0.9rem;
                    opacity: 0.9;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .kpi-change {
                    font-size: 0.85rem;
                    margin-top: 8px;
                    opacity: 0.8;
                }

                /* Content Sections */
                .filter-section {
                    background: #ffffff;
                    border: 1px solid var(--neutral-light);
                    border-radius: 16px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                    padding: 20px;
                    margin-bottom: 20px;
                }

                /* Graph Layout */
                .graphs-grid {
                    display: grid;
                    grid-template-columns: 1fr;
                    grid-auto-rows: min-content;
                    gap: 30px;
                    margin-bottom: 50px;
                }

                .graph-box {
                    background: #ffffff;
                    border: 1px solid var(--neutral-light);
                    border-radius: 16px;
                    box-shadow: 0 6px 16px rgba(31, 78, 121, 0.08);
                    padding: 20px;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                }

                .graph-box > div {
                    flex: 1;
                    min-height: 0;
                }

                /* Example Cards */
                .example-card {
                    background: #ffffff;
                    border: 1px solid var(--neutral-light);
                    border-radius: 16px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                    padding: 20px;
                    margin: 15px 0;
                }

                .score-badge {
                    background: #F7E194;
                    color: #242D31;
                    padding: 6px 14px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                    display: inline-block;
                }

                /* Copy Button */
                .copy-button {
                    background: #F7E194;
                    color: #242D31;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    cursor: pointer;
                    margin-left: 8px;
                }
                .copy-button:hover {
                    background: #E6D080;
                }

                /* Login Screen Styles */
                .login-container {
                    max-width: 400px;
                    margin: 100px auto;
                    padding: 30px;
                    background: #ffffff;
                    border: 1px solid var(--neutral-light);
                    border-radius: 16px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                    text-align: center;
                }

                .btn-primary {
                    background: #242D31 !important;
                    border-color: #242D31 !important;
                    color: #F7E194 !important;
                    font-weight: 600;
                    border-radius: 10px;
                }
                .btn-primary:hover {
                    background: #2E363A !important;
                    border-color: #2E363A !important;
                }

                .form-control {
                    border-radius: 10px;
                    border: 1px solid var(--neutral-light);
                    padding: 12px;
                }
                .form-control:focus {
                    border-color: #F7E194;
                    box-shadow: 0 0 0 0.2rem rgba(247, 225, 148, 0.25);
                }

                .demo-code-pill {
                    display: inline-block;
                    margin: 4px 6px;
                    padding: 6px 12px;
                    font-size: 13px;
                    font-weight: 500;
                    color: #242D31;
                    background-color: #F2F3EF;
                    border: 1px solid var(--neutral-light);
                    border-radius: 20px;
                    cursor: default;
                }

                /* Timestamp */
                .last-updated {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: rgba(255, 255, 255, 0.95);
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 0.75rem;
                    color: #5a6c7d;
                    border: 1px solid var(--neutral-light);
                    backdrop-filter: blur(4px);
                    z-index: 1000;
                }

                /* Page Layout */
                .page-fluid {
                    max-width: 100% !important;
                    width: 100% !important;
                    padding: 0 !important;
                    margin: 0 auto;
                    box-sizing: border-box;
                    overflow-x: hidden;
                }

                /* Responsive Design */
                @media (min-width: 768px) {
                    .graphs-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }

                @media (min-width: 1200px) {
                    .graphs-grid {
                        grid-template-columns: repeat(3, 1fr);
                    }
                }

                @media (max-width: 768px) {
                    .main-header {
                        flex-direction: column;
                        gap: 20px;
                        padding: 20px 15px;
                    }
                    
                    .title-header {
                        font-size: 2rem !important;
                    }
                    
                    .top-bar {
                        padding: 10px 15px;
                    }
                    
                    .bank-logo-section {
                        padding: 15px;
                    }
                    
                    .bank-logo {
                        max-height: 50px !important;
                        max-width: 150px !important;
                    }
                }
        """
        ),
    ),
    
    # Login Screen or Dashboard
    ui.output_ui("login_or_dashboard")
)

def server(input, output, session):
    # Reactive values
    authenticated = reactive.Value(False)
    current_bank = reactive.Value(None)
    bank_data = reactive.Value(None)
    admin_authenticated = reactive.Value(False)
    sort_column = reactive.Value("Weighted Score")
    sort_ascending = reactive.Value(False)
    
    @output
    @render.ui
    def login_or_dashboard():
        if admin_authenticated.get():
            return create_admin_dashboard_ui()
        elif not authenticated.get():
            return create_login_ui()
        else:
            return create_dashboard_ui()
    
    def create_login_ui():
        return ui.div(
            ui.output_ui("sailpeak_logo"),
            ui.div(
                ui.div("🏦", style="font-size: 3em; margin-bottom: 20px;"),
                ui.h2("Bank Websites CEFR B2 Compliancy Analysis"),
                ui.h4("Created by Sailpeak AI Lab", style="color: #242D31; margin-bottom: 20px;"),
                ui.p("Enter demo access code to explore B2 compliancy insights", 
                    style="color: #36464B; margin-bottom: 30px;"),

                # Bank logo preview if valid
                ui.output_ui("login_bank_logo"),

                # Input field and live icon feedback
                ui.div(
                    ui.input_text("access_code", "", placeholder="Demo access code or admin password"),
                    style="display: flex; justify-content: center; margin-bottom: 20px;"
                ),

                # Submit button
                ui.input_action_button("login_btn", "View Dashboard", 
                    style="background: #242D31; color: #F7E194; padding: 12px 24px; border: none; border-radius: 10px; width: 100%; font-weight: 600;"),

                ui.br(), ui.br(),

                class_="login-container"
            )
        )

    def create_dashboard_ui():
        bank_info = BANK_CONFIG[current_bank.get()]
        
        return ui.div(
            
            # MAIN DASHBOARD CONTENT (wrapped for fade-in)
            ui.div(
                # NEW PROFESSIONAL HEADER STRUCTURE
                ui.div(
                    # Top bar with logout and Sailpeak branding
                    ui.div(
                        # Logout button
                        ui.div(
                            ui.input_action_button("logout_btn", "← Back to Login", class_="logout-btn"),
                            class_="logout-container"
                        ),
                        # Sailpeak branding
                        ui.div(
                            ui.output_ui("sailpeak_logo_box"),
                            ui.span("AI Lab", class_="sailpeak-text"),
                            class_="sailpeak-top-bar"
                        ),
                        class_="top-bar"
                    ),
                    
                    # Main header with bank logo and title
                    ui.div(
                        # Bank logo section
                        ui.div(
                            ui.output_ui("bank_logo_box"),
                            class_="bank-logo-section"
                        ),
                        
                        # Title section
                        ui.div(
                            ui.h1("CEFR B2 Compliance Analysis", class_="title-header"),
                            ui.div("Website Accessibility Assessment", class_="title-subtitle"),
                            class_="title-section-new"
                        ),
                        
                        class_="main-header"
                    ),
                    
                    class_="header-container"
                ),

                # KPI Cards Section - FIXED FOR FULL WIDTH
                ui.div(
                    ui.div(
                        ui.output_ui("score_cards_row"),
                        class_="score-cards-container"
                    ),
                    class_="kpi-wrapper"
                ),

                # Key Findings - Full width, always use full dataset (unfiltered)
                ui.div(
                    ui.h3("🎯 Overall Key Findings"),
                    ui.output_ui("key_insights_unfiltered"),
                    class_="filter-section",
                    style="margin-bottom: 30px;"
                ),
                
                # Main content area - full width now
                ui.div(
                    # Results Section - put everything in one big white box
                    ui.div(
                        ui.h2("📊 Performance Analysis", style="color: #1f4e79; margin-bottom: 20px; font-weight: 600;"),
                        
                        # Graph Filters (inside the white box, under the title)
                        ui.div(
                            ui.h4("📊 Graph Filters", style="margin-bottom: 15px; color: #242D31;"),
                            ui.div(
                                "💡 Please select your filter preferences below to load the performance charts",
                                style="background: #F2F3EF; color: #242D31; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; border-left: 3px solid #F7E194;"
                            ),
                            ui.row(
                                ui.column(6, ui.input_select("language_filter", "Language:", choices={})),
                                ui.column(6, ui.input_select("page_type_filter", "Content Type:", choices={}))
                            ),
                            style="margin-bottom: 30px; padding: 15px; background: #F9F9F9; border-radius: 12px;"
                        ),
                        
                        # Graphs grid
                        ui.div(
                            ui.div(ui.output_ui("performance_overview"), class_="graph-box"),
                            ui.div(ui.output_ui("page_type_analysis"), class_="graph-box"),
                            ui.div(ui.output_ui("detailed_scores_breakdown"), class_="graph-box"),
                            class_="graphs-grid"
                        ),
                        
                        class_="filter-section",  # This creates the big white box
                        style="margin-bottom: 40px;"
                    ),
                    
                    # Example URLs Section with its own filter
                    ui.div(
                        ui.h2("🔍 Page Examples & Insights", style="color: #242D31; margin-bottom: 20px;"),
                        ui.div(
                            ui.h4("🔍 Example Filters", style="margin-bottom: 15px; color: #242D31;"),
                            ui.row(
                                ui.column(4, ui.input_select("example_language_filter", "Language:", choices={})),
                                ui.column(4, ui.input_select("example_page_type_filter", "Content Type:", choices={})),
                                ui.column(4, ui.input_select("example_score_range", "Score Range:", 
                                    choices={"all": "All Ranges", "high": "70-90%", "medium": "40-70%", "low": "10-40%"}, 
                                    selected="all"))
                            ),
                            class_="filter-section",
                            style="margin-bottom: 20px;"
                        ),
                        ui.p("Sample pages from your analysis with specific insights:", 
                                style="color: #36464B; margin-bottom: 20px; font-size: 16px;"),
                        ui.output_ui("example_urls"),
                        class_="filter-section"
                    )
                ),
                
                # Timestamp (positioned at bottom right via CSS)
                ui.output_ui("last_updated_timestamp"),
                
                class_="dashboard-content",
            )
        )
    
    def create_admin_dashboard_ui():
        return ui.div(
            # Header
            ui.div(
                ui.div(
                    ui.h1("🛠️ Admin Dashboard", style="color: #242D31; margin: 0;"),
                    ui.input_action_button("admin_logout_btn", "← Back to Login", 
                        style="background: #6c757d; color: white; padding: 8px 16px; border: none; border-radius: 6px;"),
                    style="display: flex; justify-content: space-between; align-items: center; padding: 20px 30px; background: white; border-bottom: 1px solid #e9ecef;"
                )
            ),
            
            # Admin content
            ui.div(
                ui.h2("🏆 Bank Rankings", style="color: #242D31; margin-bottom: 30px;"),
                
                # Rankings table
                ui.output_ui("admin_rankings_table"),
                
                style="padding: 30px; max-width: 1200px; margin: 0 auto;"
            ),
            
            class_="admin-dashboard"
        )
    
    # Authentication logic
    @reactive.Effect
    @reactive.event(input.login_btn)
    def handle_login():
        access_code = input.access_code()
        if access_code == ADMIN_CONFIG["admin_password"]:
            admin_authenticated.set(True)
            authenticated.set(False)
        elif access_code in BANK_CONFIG:
            authenticated.set(True)
            admin_authenticated.set(False)
            current_bank.set(access_code)
            load_bank_data(access_code)
        
    @reactive.Effect
    @reactive.event(input.logout_btn)
    def handle_logout():
        authenticated.set(False)
        current_bank.set(None)
        bank_data.set(None)

    @reactive.Effect
    @reactive.event(input.admin_logout_btn)
    def handle_admin_logout():
        admin_authenticated.set(False)

    @reactive.Effect
    @reactive.event(input.sort_bank)
    def sort_by_bank():
        if sort_column.get() == "Bank":
            sort_ascending.set(not sort_ascending.get())
        else:
            sort_column.set("Bank")
            sort_ascending.set(True)

    @reactive.Effect
    @reactive.event(input.sort_weighted_score)
    def sort_by_weighted_score():
        if sort_column.get() == "Weighted Score":
            sort_ascending.set(not sort_ascending.get())
        else:
            sort_column.set("Weighted Score")
            sort_ascending.set(False)

    @reactive.Effect
    @reactive.event(input.sort_simple_average)
    def sort_by_simple_average():
        if sort_column.get() == "Simple Average":
            sort_ascending.set(not sort_ascending.get())
        else:
            sort_column.set("Simple Average")
            sort_ascending.set(False)

    @reactive.Effect
    @reactive.event(input.sort_total_pages)
    def sort_by_total_pages():
        if sort_column.get() == "Total Pages":
            sort_ascending.set(not sort_ascending.get())
        else:
            sort_column.set("Total Pages")
            sort_ascending.set(False)

    @reactive.Effect
    @reactive.event(input.sort_compliance_rate)
    def sort_by_compliance_rate():
        if sort_column.get() == "Compliance Rate":
            sort_ascending.set(not sort_ascending.get())
        else:
            sort_column.set("Compliance Rate")
            sort_ascending.set(False)
    
    def load_bank_data(bank_code):
        try:
            bank_info = BANK_CONFIG[bank_code]
            file_path = bank_info["file"]
            
            if os.path.exists(file_path):
                df = pd.read_excel(file_path)
                
                # Clean column names
                df.columns = df.columns.str.strip()
                
                # Check for required columns and create defaults if needed
                required_columns = ['URL', 'Page Type', 'Compliance Level', 'Vocabulary Complexity', 
                                  'Grammatical Structures', 'Overall Clarity', 'Coherence']
                
                for col in required_columns:
                    if col not in df.columns:
                        if col == 'URL':
                            df[col] = f"https://www.{bank_info['name'].lower().replace(' ', '')}.be/sample"
                        elif col == 'Page Type':
                            df[col] = 'Other'
                        else:
                            df[col] = 50
                
            else:
                # Create sample data if file doesn't exist
                sample_data = create_sample_data(bank_info["name"])
                df = pd.DataFrame(sample_data)
            
            # Extract language from URL
            df['Language'] = df['URL'].apply(lambda x: 'French' if '/fr/' in str(x) else 'Dutch' if '/nl/' in str(x) else 'English' if '/en/' in str(x) else 'German' if '/de/' in str(x) else 'Unknown')
            
            # Ensure numeric columns are actually numeric
            numeric_columns = ['Compliance Level', 'Vocabulary Complexity', 'Grammatical Structures', 'Overall Clarity', 'Coherence']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(50)
            
            # Store the data
            bank_data.set(df)
            
            # Update filter options
            languages = ['All'] + sorted(df['Language'].unique().tolist())
            page_types = ['All'] + sorted(df['Page Type'].dropna().unique().tolist())
            
            ui.update_select("language_filter", choices=languages, selected="All")
            ui.update_select("page_type_filter", choices=page_types, selected="All")
            ui.update_select("example_language_filter", choices=languages, selected="All")
            ui.update_select("example_page_type_filter", choices=page_types, selected="All")
            
        except Exception as e:
            print(f"Error loading data for {bank_code}: {e}")
            try:
                bank_info = BANK_CONFIG[bank_code]
                sample_data = create_sample_data(bank_info["name"])
                df = pd.DataFrame(sample_data)
                df['Language'] = df['URL'].apply(lambda x: 'French' if '/fr/' in str(x) else 'Dutch' if '/nl/' in str(x) else 'English' if '/en/' in str(x) else 'German' if '/de/' in str(x) else 'Unknown')
                bank_data.set(df)
                
                languages = ['All'] + sorted(df['Language'].unique().tolist())
                page_types = ['All'] + sorted(df['Page Type'].dropna().unique().tolist())
                
                ui.update_select("language_filter", choices=languages, selected="All")
                ui.update_select("page_type_filter", choices=page_types, selected="All")
            except:
                bank_data.set(pd.DataFrame())
    
    def create_sample_data(bank_name):
        """Create sample data for demo purposes"""
        base_url = f"https://www.{bank_name.lower().replace(' ', '')}.be"
        return {
            'URL': [
                f'{base_url}/fr/particulier/',
                f'{base_url}/nl/particulier/',
                f'{base_url}/fr/entreprises/',
                f'{base_url}/nl/ondernemingen/',
                f'{base_url}/fr/contact/',
                f'{base_url}/nl/contact/'
            ],
            'Page Type': ['Other', 'Other', 'Product', 'Product', 'Contact', 'Contact'],
            'Compliance Level': [75, 65, 68, 65, 80, 72],
            'Vocabulary Complexity': [7, 6, 6, 6, 5, 5],
            'Grammatical Structures': [8, 7, 8, 7, 8, 7],
            'Overall Clarity': [7, 6, 6, 6, 8, 7],
            'Coherence': [8, 7, 7, 7, 8, 8],
            'Rationale': [f'Analysis for {bank_name}...'] * 6
        }
    
    @output
    @render.ui
    def last_updated_timestamp():
        from datetime import datetime
        import pytz
        
        # Get current time in CET
        cet = pytz.timezone('CET')
        current_time = datetime.now(cet)
        formatted_time = current_time.strftime("%b %d, %Y, %H:%M CET")
        
        return ui.div(
            f"Last updated {formatted_time}",
            class_="last-updated"
        )

    @output
    @render.ui
    def sailpeak_logo():
        logo_path = "logos/sailpeak-logo.png"
        
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f:
                    logo_data = base64.b64encode(f.read()).decode()
                    logo_src = f"data:image/png;base64,{logo_data}"
                    
                    return ui.img(src=logo_src, class_="sailpeak-logo", alt="Sailpeak Logo")
                    
            except Exception as e:
                print(f"Error loading Sailpeak logo: {e}")
        
        # Fallback
        return ui.img(src="https://via.placeholder.com/120x40/242D31/F7E194?text=SAILPEAK", 
                      class_="sailpeak-logo", alt="Sailpeak Logo")
    
    @output
    @render.ui
    def sailpeak_logo_box():
        logo_path = "logos/sailpeak-logo.png"
        
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f:
                    logo_data = base64.b64encode(f.read()).decode()
                    logo_src = f"data:image/png;base64,{logo_data}"
                    
                    return ui.img(src=logo_src, class_="sailpeak-logo", alt="Sailpeak Logo")
                    
            except Exception as e:
                print(f"Error loading Sailpeak logo: {e}")
        
        # Fallback
        return ui.img(src="https://via.placeholder.com/120x40/242D31/F7E194?text=SAILPEAK", 
                      class_="sailpeak-logo", alt="Sailpeak Logo")
    
    @output
    @render.ui
    def bank_logo_box():
        if not authenticated.get():
            return ui.div()
        
        bank_info = BANK_CONFIG[current_bank.get()]
        logo_path = bank_info['logo_path']
        
        print(f"Debug: Current working directory: {os.getcwd()}")
        print(f"Debug: Looking for logo at: {logo_path}")
        print(f"Debug: Logo file exists: {os.path.exists(logo_path)}")
        
        # Check if logo file exists
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f:
                    logo_data = base64.b64encode(f.read()).decode()
                    file_ext = logo_path.split('.')[-1].lower()
                    
                    # Handle different file types
                    mime_types = {
                        'webp': 'image/webp',
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        'gif': 'image/gif'
                    }
                    
                    mime_type = mime_types.get(file_ext, 'image/png')
                    logo_src = f"data:{mime_type};base64,{logo_data}"
                    
                    print(f"Debug: Successfully loaded logo, size: {len(logo_data)} chars")
                    
                    return ui.div(
                        ui.img(src=logo_src, class_="bank-logo", alt=f"{bank_info['name']} Logo")
                    )
                    
            except Exception as e:
                print(f"Error loading logo {logo_path}: {e}")
                # Fall through to placeholder
        else:
            print(f"Logo file not found: {logo_path}")
            # Also check absolute path
            abs_path = os.path.abspath(logo_path)
            print(f"Debug: Absolute path would be: {abs_path}")
        
        # Fallback placeholder using Sailpeak colors
        bank_name_encoded = bank_info['name'].upper().replace(' ', '+')
        placeholder_url = f"https://via.placeholder.com/160x60/242D31/F7E194?text={bank_name_encoded}"
        
        return ui.div(
            ui.img(src=placeholder_url, class_="bank-logo", alt=f"{bank_info['name']} Logo Placeholder"),
            ui.div(f"📁 {logo_path}", class_="logo-debug"),
            ui.div(f"❌ File not found", class_="logo-debug")
        )
    
    @output
    @render.ui
    def login_bank_logo():
        code = input.access_code()
        if code in BANK_CONFIG:
            logo_path = BANK_CONFIG[code]['logo_path']
            if os.path.exists(logo_path):
                try:
                    with open(logo_path, "rb") as f:
                        ext = logo_path.split('.')[-1].lower()
                        mime = "image/png" if ext == "png" else f"image/{ext}"
                        logo_data = base64.b64encode(f.read()).decode()
                        return ui.img(
                            src=f"data:{mime};base64,{logo_data}", 
                            style="height: 50px; margin-bottom: 20px;"
                        )
                except Exception as e:
                    print(f"Error loading logo: {e}")
        return ""

    @reactive.Calc
    def filtered_data():
        df = bank_data.get()
        if df is None or df.empty:
            return pd.DataFrame()

        filtered = df.copy()
        
        # Use "All" as default if filter is None or empty
        lang_filter = input.language_filter() or "All"
        page_filter = input.page_type_filter() or "All"
        
        if lang_filter != 'All':
            filtered = filtered[filtered['Language'] == lang_filter]
        
        if page_filter != 'All':
            filtered = filtered[filtered['Page Type'] == page_filter]
        
        return filtered
    
    @reactive.Calc
    def filtered_examples_data():
        if not authenticated.get():
            return pd.DataFrame()
            
        df = bank_data.get()
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Apply example-specific filters
        filtered = df.copy()
        
        if input.example_language_filter() != 'All':
            filtered = filtered[filtered['Language'] == input.example_language_filter()]
        
        if input.example_page_type_filter() != 'All':
            filtered = filtered[filtered['Page Type'] == input.example_page_type_filter()]
        
        # Apply score range filter
        score_range = input.example_score_range()
        if score_range == 'high':
            filtered = filtered[(filtered['Compliance Level'] >= 70) & (filtered['Compliance Level'] <= 90)]
        elif score_range == 'medium':
            filtered = filtered[(filtered['Compliance Level'] >= 40) & (filtered['Compliance Level'] < 70)]
        elif score_range == 'low':
            filtered = filtered[(filtered['Compliance Level'] >= 10) & (filtered['Compliance Level'] < 40)]
        
        return filtered

    @output
    @render.ui
    def score_cards_row():
        if not authenticated.get():
            return ui.div()
            
        # Always use full dataset for calculations (never filtered)
        full_df = bank_data.get()
        if full_df is None or full_df.empty:
            return ui.div()
        
        overall_score = full_df['Compliance Level'].mean()
        total_pages = len(full_df)

        # Calculate accessibility percentages from full dataset
        accessible_pages = len(full_df[full_df['Compliance Level'] >= 70])
        not_accessible_pages = total_pages - accessible_pages
        accessible_percent = (accessible_pages / total_pages * 100) if total_pages > 0 else 0
        not_accessible_percent = (not_accessible_pages / total_pages * 100) if total_pages > 0 else 0

        # Calculate industry benchmark and ranking in single loop
        bank_scores_with_names = []
        all_bank_scores = []
        for bank_code, bank_info in BANK_CONFIG.items():
            try:
                if os.path.exists(bank_info["file"]):
                    benchmark_df = pd.read_excel(bank_info["file"])
                    benchmark_df.columns = benchmark_df.columns.str.strip()
                    
                    if 'Compliance Level' in benchmark_df.columns and 'Page Type' in benchmark_df.columns:
                        benchmark_df['Compliance Level'] = pd.to_numeric(benchmark_df['Compliance Level'], errors='coerce')
                        benchmark_df = benchmark_df.dropna(subset=['Compliance Level'])
                        
                        # Use weighted scoring instead of simple average
                        bank_avg = calculate_weighted_score(benchmark_df)
                        
                        if not pd.isna(bank_avg):
                            bank_scores_with_names.append((bank_info["name"], bank_avg))
                            if bank_code != current_bank.get():  # Exclude current bank from average
                                all_bank_scores.append(bank_avg)
            except:
                continue

        industry_avg = sum(all_bank_scores) / len(all_bank_scores) if all_bank_scores else 58
        benchmark_diff = overall_score - industry_avg

        # Sort by score (highest first) and find current bank's rank
        bank_scores_with_names.sort(key=lambda x: x[1], reverse=True)
        current_bank_name = BANK_CONFIG[current_bank.get()]["name"]
        total_banks = len(bank_scores_with_names)

        # Find rank
        rank = next((i+1 for i, (name, score) in enumerate(bank_scores_with_names) if name == current_bank_name), None)
        
        # Calculate accessibility percentages from full dataset
        accessible_pages = len(full_df[full_df['Compliance Level'] >= 70])
        not_accessible_pages = total_pages - accessible_pages
        high_performers = len(full_df[full_df['Compliance Level'] >= 80])
        needs_attention = len(full_df[full_df['Compliance Level'] < 60])
        
        bank_info = BANK_CONFIG[current_bank.get()]
        primary = bank_info.get("color_primary", "#4A90E2")
        secondary = bank_info.get("color_secondary", "#357ABD")

        card_style = (
            f"background: linear-gradient(135deg, {primary}, {secondary});"
            "color: white; border-radius: 16px; padding: 24px; text-align: center;"
            "flex: 1; min-height: 140px; display: flex; flex-direction: column; justify-content: center;"
        )

        return ui.div(
            # Total Pages Card
            ui.div(
                ui.h4("TOTAL PAGES", style="color: white; font-size: 14px; font-weight: 500; margin-bottom: 10px; text-transform: uppercase;"),
                ui.div(f"{total_pages:,}", style="font-size: 3em; font-weight: bold; color: white; margin: 10px 0;"),
                style=card_style
            ),
            
            # Average Compliance Card
            ui.div(
                ui.h4("AVG COMPLIANCE", style="color: white; font-size: 14px; font-weight: 500; margin-bottom: 10px; text-transform: uppercase;"),
                ui.div(f"{overall_score:.1f}%", style="font-size: 3em; font-weight: bold; color: white; margin: 10px 0;"),
                style=card_style
            ),

            # B2 Compliant Pages Card
            ui.div(
            ui.h4("B2 COMPLIANT PAGES", style="color: white; font-size: 14px; font-weight: 500; margin-bottom: 10px; text-transform: uppercase;"),
            ui.div(f"{accessible_pages}", style="font-size: 3em; font-weight: bold; color: white; margin: 10px 0;"),
            ui.p(f"{accessible_percent:.1f}% pages ≥70%", style="color: rgba(255,255,255,0.8); margin: 0; font-size: 12px;"),
            style=card_style
            ),

            # B2 Non-Compliant Pages Card
            ui.div(
            ui.h4("NON-COMPLIANT PAGES", style="color: white; font-size: 14px; font-weight: 500; margin-bottom: 10px; text-transform: uppercase;"),
            ui.div(f"{not_accessible_pages}", style="font-size: 3em; font-weight: bold; color: white; margin: 10px 0;"),
            ui.p(f"{not_accessible_percent:.1f}% pages <70%", style="color: rgba(255,255,255,0.8); margin: 0; font-size: 12px;"),
            style=card_style
            ),

            # Industry Ranking Card
            ui.div(
                ui.h4("INDUSTRY RANKING", style="color: white; font-size: 14px; font-weight: 500; margin-bottom: 10px; text-transform: uppercase;"),
                ui.div(f"#{rank}" if rank else "N/A", style="font-size: 3em; font-weight: bold; color: white; margin: 10px 0;"),
                ui.p(f"{benchmark_diff:+.0f}% vs avg", style="color: rgba(255,255,255,0.8); margin: 0; font-size: 12px;"),
                style=card_style
            ),
            
            class_="score-cards-container"
        )
    
    @output
    @render.ui
    def performance_overview():
        if not authenticated.get():
            return ui.div()
            
        df = filtered_data()
        if df.empty:
            return ui.div("No data available", style="text-align: center; padding: 40px; color: #36464B;")
        
        bank_info = BANK_CONFIG[current_bank.get()]
        
        # Score range binning
        def get_score_range(score):
            if score < 50:
                return '0–50'
            elif score < 60:
                return '50–60'
            elif score < 70:
                return '60–70'
            elif score < 80:
                return '70–80'
            else:
                return '80+'

        df['Score_Range'] = df['Compliance Level'].apply(get_score_range)
        range_order = ['0–50', '50–60', '60–70', '70–80', '80+']
        range_counts = df['Score_Range'].value_counts().reindex(range_order, fill_value=0)

        # Insight text (optional)
        most_common_range = range_counts.idxmax()
        count_most_common = range_counts.max()
        insight_text = (
            f"Most pages fall in the <b>{most_common_range}</b>% range "
            f"({count_most_common} pages), showing where the bulk of performance lies."
        )

        # Plot
        fig = px.bar(
            x=range_order, 
            y=range_counts.values,
            title='📊 Accessibility Score Distribution',
            labels={'x': 'Score Range (%)', 'y': 'Number of Pages'},
            color_discrete_sequence=['#242D31']
        )
        
        fig.update_traces(
            text=range_counts.values,
            textposition='inside',
            textfont_size=14,
            textfont_color='#ffffff'
        )

        fig.update_layout(
            showlegend=False, 
            height=300,
            title_font_size=18,
            title_font_color='#242D31',
            plot_bgcolor='#F2F3EF',
            paper_bgcolor='#F2F3EF',
            font_color='#242D31',
            margin=dict(t=50, b=50, l=60, r=30),
            xaxis=dict(
                tickfont_color='#36464B'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(36, 45, 49, 0.1)',
                tickfont_color='#5a6c7d'
            )
        )

        fig_id = f"score_dist_{uuid4().hex}"

        return ui.div(
            ui.HTML(fig.to_html(include_plotlyjs="cdn", div_id=fig_id, config={'displayModeBar': False})),
            ui.div(
                ui.HTML(f"<small style='color: #5a6c7d; font-style: italic;'>{insight_text}</small>"),
                style="margin-top: 8px; padding: 0 15px;"
            ),
            style="height: 100%; width: 100%; margin: 0; padding: 0;"
        )

    @output
    @render.ui
    def page_type_analysis():
        if not authenticated.get():
            return ui.div()
            
        df = filtered_data()
        if df.empty:
            return ui.div("No data available", style="text-align: center; padding: 40px; color: #36464B;")

        bank_info = BANK_CONFIG[current_bank.get()]
        
        # Calculate current bank's page type performance
        page_stats = df.groupby('Page Type')['Compliance Level'].mean().round(1)
        
        # Calculate industry averages for each page type
        industry_page_stats = {}
        all_banks_data = []
        
        for bank_code, bank_config in BANK_CONFIG.items():
            if bank_code == current_bank.get():  # Skip current bank
                continue
                
            try:
                if os.path.exists(bank_config["file"]):
                    industry_df = pd.read_excel(bank_config["file"])
                    industry_df.columns = industry_df.columns.str.strip()
                    
                    if 'Compliance Level' in industry_df.columns and 'Page Type' in industry_df.columns:
                        # Extract language from URL if available
                        if 'URL' in industry_df.columns:
                            industry_df['Language'] = industry_df['URL'].apply(
                                lambda x: 'French' if '/fr/' in str(x) else 'Dutch' if '/nl/' in str(x) else 'English' if '/en/' in str(x) else 'Unknown'
                            )
                        else:
                            industry_df['Language'] = 'Unknown'
                        
                        # Convert to numeric
                        industry_df['Compliance Level'] = pd.to_numeric(industry_df['Compliance Level'], errors='coerce')
                        industry_df = industry_df.dropna(subset=['Compliance Level'])
                        
                        # Add bank name for tracking
                        industry_df['Bank'] = bank_config['name']
                        all_banks_data.append(industry_df)
            except Exception as e:
                print(f"Error loading industry data for {bank_code}: {e}")
                continue
        
        # Combine all industry data
        if all_banks_data:
            combined_industry_df = pd.concat(all_banks_data, ignore_index=True)
            industry_page_stats = combined_industry_df.groupby('Page Type')['Compliance Level'].mean().round(1)
        else:
            # Fallback industry averages if no data available
            industry_page_stats = pd.Series({
                'Contact': 68,
                'Product': 62,
                'Legal': 58,
                'Other': 65,
                'Home': 70
            })
        
        # Only use page types that exist in current bank's data
        existing_page_types = set(page_stats.index)  # Only current bank's page types

        plot_data = []
        for page_type in existing_page_types:
            current_score = page_stats[page_type]  # Direct access, no default 0
            industry_score = industry_page_stats.get(page_type, 60)  # Industry default is OK
            
            plot_data.append({
                'Page Type': page_type,
                'Current Bank': current_score,
                'Industry Average': industry_score
            })
        
        plot_df = pd.DataFrame(plot_data)
        
        # Sort by current bank performance
        plot_df = plot_df.sort_values('Current Bank', ascending=True)
        
        # Create grouped bar chart
        fig = go.Figure()
        
        # Add current bank bars
        fig.add_trace(go.Bar(
            name=bank_info['name'],
            x=plot_df['Page Type'],
            y=plot_df['Current Bank'],
            marker_color=bank_info['color_primary'],
            text=[f"{val:.0f}%" for val in plot_df['Current Bank']],
            textposition='outside',
            textfont=dict(color=bank_info['color_primary'], size=12)
        ))
        
        # Add industry average bars
        fig.add_trace(go.Bar(
            name='Industry Average',
            x=plot_df['Page Type'],
            y=plot_df['Industry Average'],
            marker_color='#8b9dc3',
            text=[f"{val:.0f}%" for val in plot_df['Industry Average']],
            textposition='outside',
            textfont=dict(color='#5a6c7d', size=11)
        ))
        
        # Update layout
        chart_height = max(280, len(plot_df) * 50)
        
        fig.update_layout(
            title='📋 Content Type Performance vs Industry',
            xaxis_title='Page Type',
            yaxis_title='Average Score (%)',
            barmode='group',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=chart_height,
            title_font_size=18,
            title_font_color='#242D31',
            plot_bgcolor='#F2F3EF',
            paper_bgcolor='#F2F3EF',
            font_color='#242D31',
            margin=dict(t=80, b=70, l=60, r=30),
            yaxis=dict(
                range=[0, 100],
                ticksuffix='%',
                showgrid=True,
                gridcolor='rgba(36, 45, 49, 0.1)',
                tickfont_size=10,
                tickfont_color='#5a6c7d'
            ),
            xaxis=dict(
                tickangle=45,
                tickfont_size=11,
                tickfont_color='#36464B',
                showgrid=False
            )
        )
        
        # Generate enhanced insights
        best_performer = plot_df.loc[plot_df['Current Bank'].idxmax()]
        worst_performer = plot_df.loc[plot_df['Current Bank'].idxmin()]
        
        # Calculate performance vs industry
        outperforming = plot_df[plot_df['Current Bank'] > plot_df['Industry Average']]
        underperforming = plot_df[plot_df['Current Bank'] < plot_df['Industry Average']]
        
        if len(outperforming) > 0:
            best_vs_industry = outperforming.loc[
                (outperforming['Current Bank'] - outperforming['Industry Average']).idxmax()
            ]
            outperform_text = f"<b>{best_vs_industry['Page Type']}</b> outperforms industry by {best_vs_industry['Current Bank'] - best_vs_industry['Industry Average']:.0f} points. "
        else:
            outperform_text = ""
        
        if len(underperforming) > 0:
            worst_vs_industry = underperforming.loc[
                (underperforming['Industry Average'] - underperforming['Current Bank']).idxmax()
            ]
            underperform_text = f"<b>{worst_vs_industry['Page Type']}</b> lags industry by {worst_vs_industry['Industry Average'] - worst_vs_industry['Current Bank']:.0f} points."
        else:
            underperform_text = "All content types meet or exceed industry standards."
        
        insight_text = (
            f"Your strongest content type is <b>{best_performer['Page Type']}</b> at {best_performer['Current Bank']:.0f}%. "
            f"{outperform_text}{underperform_text}"
        )

        fig_id = f"page_type_analysis_{uuid4().hex}"

        return ui.div(
            ui.div(
                ui.HTML(fig.to_html(include_plotlyjs="cdn", div_id=fig_id, config={'displayModeBar': False})),
                ui.div(
                    ui.HTML(f"<small style='color: #5a6c7d; font-style: italic;'>{insight_text}</small>"),
                    style="margin-top: 8px; padding: 0 15px;"
                ),
            ),
        )
    @output
    @render.ui
    def detailed_scores_breakdown():
        if not authenticated.get():
            return ui.div()

        df = filtered_data()
        if df.empty:
            return ui.div("No data available", style="text-align: center; padding: 40px; color: #36464B;")

        # Define categories and compute their means
        categories = ['Vocabulary\nComplexity', 'Grammatical\nStructures', 'Overall\nClarity', 'Coherence']
        scores = [
            df['Vocabulary Complexity'].mean(),
            df['Grammatical Structures'].mean(),
            df['Overall Clarity'].mean(),
            df['Coherence'].mean()
        ]

        # Identify strongest and weakest components
        max_cat = categories[scores.index(max(scores))].replace('\n', ' ')
        min_cat = categories[scores.index(min(scores))].replace('\n', ' ')
        insight_text = (
            f"<b>{max_cat}</b> scores highest ({max(scores):.1f}), "
            f"while <b>{min_cat}</b> may need attention ({min(scores):.1f})."
        )

        # Plot the bar chart
        fig = px.bar(
            x=categories,
            y=scores,
            title='📋 Detailed Component Scores (1–10 Scale)',
            labels={'x': '', 'y': 'Average Score (1–10)'},
            color_discrete_sequence=['#8B1538']
        )

        fig.update_traces(
            text=[f"{score:.1f}" for score in scores],
            textposition='inside',
            textfont_color='#ffffff',
            textfont_size=14
        )

        fig.update_xaxes(
            tickangle=-30,
            tickfont_size=11,
            tickfont_color='#36464B'
        )

        fig.update_layout(
            showlegend=False,
            height=300,
            title_font_size=18,
            title_font_color='#242D31',
            plot_bgcolor='#F2F3EF',
            paper_bgcolor='#F2F3EF',
            font_color='#242D31',
            margin=dict(t=50, b=70, l=60, r=30),
            yaxis=dict(
                range=[0, 10],
                dtick=1,
                showgrid=True,
                gridcolor='rgba(36, 45, 49, 0.1)',
                tickfont_color='#5a6c7d'
            )
        )

        fig_id = f"detailed_scores_{uuid4().hex}"

        return ui.div(
            ui.div(
                ui.HTML(fig.to_html(include_plotlyjs="cdn", div_id=fig_id, config={'displayModeBar': False})),
                ui.div(
                    ui.HTML(f"<small style='color: #5a6c7d; font-style: italic;'>{insight_text}</small>"),
                    style="margin-top: 8px; padding: 0 15px;"
                ),
            ),
        )

    @output
    @render.ui
    def admin_rankings_table():
        if not admin_authenticated.get():
            return ui.div()
        
        # Collect all bank data
        all_bank_data = []
        
        for bank_code, bank_info in BANK_CONFIG.items():
            try:
                if os.path.exists(bank_info["file"]):
                    df = pd.read_excel(bank_info["file"])
                    df.columns = df.columns.str.strip()
                    
                    if 'Compliance Level' in df.columns and 'Page Type' in df.columns:
                        df['Compliance Level'] = pd.to_numeric(df['Compliance Level'], errors='coerce')
                        df = df.dropna(subset=['Compliance Level'])
                        
                        # Calculate metrics
                        weighted_score = calculate_weighted_score(df)
                        simple_avg = df['Compliance Level'].mean()
                        total_pages = len(df)
                        compliant_pages = len(df[df['Compliance Level'] >= 70])
                        compliance_rate = (compliant_pages / total_pages * 100) if total_pages > 0 else 0
                        
                        # Page type distribution
                        page_type_counts = df['Page Type'].value_counts()
                        page_type_dist = ', '.join([f"{pt}: {count}" for pt, count in page_type_counts.head(3).items()])
                        
                        all_bank_data.append({
                            'Bank': bank_info['name'],
                            'Weighted Score': weighted_score,
                            'Simple Average': simple_avg,
                            'Total Pages': total_pages,
                            'Compliance Rate': compliance_rate,
                            'Top Page Types': page_type_dist
                        })
            except Exception as e:
                print(f"Error processing {bank_info['name']}: {e}")
                continue
        
        if not all_bank_data:
            return ui.div("No data available")
        
        # Sort data based on current sort column and direction
        current_sort = sort_column.get()
        ascending = sort_ascending.get()
        
        if current_sort in ['Weighted Score', 'Simple Average', 'Total Pages', 'Compliance Rate']:
            all_bank_data.sort(key=lambda x: x[current_sort], reverse=not ascending)
        else:  # Bank name
            all_bank_data.sort(key=lambda x: x['Bank'], reverse=not ascending)
        
        # Create sortable header function
        def create_sortable_header(column_name, display_name):
            current_sort = sort_column.get()
            ascending = sort_ascending.get()
            
            # Determine arrow
            if current_sort == column_name:
                arrow = " ↑" if ascending else " ↓"
            else:
                arrow = ""
            
            return ui.tags.th(
                ui.input_action_button(
                    f"sort_{column_name.replace(' ', '_').lower()}", 
                    f"{display_name}{arrow}",
                    style="background: none; border: none; color: #242D31; font-weight: 600; cursor: pointer; padding: 12px;"
                ),
                style="padding: 0; background: #f8f9fa;"
            )
        
        # Create table rows
        table_rows = []
        for i, bank in enumerate(all_bank_data, 1):
            # Color coding for weighted vs simple average
            weighted_color = "#00A550" if bank['Weighted Score'] > bank['Simple Average'] else "#dc3545"
            
            table_rows.append(
                ui.tags.tr(
                    ui.tags.td(f"#{i}", style="font-weight: bold; color: #242D31; padding: 12px;"),
                    ui.tags.td(bank['Bank'], style="font-weight: 600; padding: 12px;"),
                    ui.tags.td(f"{bank['Weighted Score']:.1f}%", 
                              style=f"color: {weighted_color}; font-weight: bold; padding: 12px;"),
                    ui.tags.td(f"{bank['Simple Average']:.1f}%", style="color: #6c757d; padding: 12px;"),
                    ui.tags.td(f"{bank['Total Pages']}", style="text-align: center; padding: 12px;"),
                    ui.tags.td(f"{bank['Compliance Rate']:.1f}%", style="text-align: center; padding: 12px;"),
                    ui.tags.td(bank['Top Page Types'], style="font-size: 12px; color: #5a6c7d; padding: 12px;"),
                    style="border-bottom: 1px solid #e9ecef;"
                )
            )
        
        return ui.div(
            ui.div(
                "💡 Green weighted scores indicate benefit from weighting, red indicates penalty",
                style="background: #e3f2fd; color: #1976d2; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 14px;"
            ),
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Rank", style="padding: 12px; background: #f8f9fa; font-weight: 600;"),
                        create_sortable_header("Bank", "Bank"),
                        create_sortable_header("Weighted Score", "Weighted Score"),
                        create_sortable_header("Simple Average", "Simple Average"),
                        create_sortable_header("Total Pages", "Total Pages"),
                        create_sortable_header("Compliance Rate", "Compliance Rate"),
                        ui.tags.th("Top Page Types", style="padding: 12px; background: #f8f9fa; font-weight: 600;"),
                    )
                ),
                ui.tags.tbody(*table_rows),
                style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
            )
        )


    @output
    @render.ui
    def example_urls():
        if not authenticated.get():
            return ui.div()
            
        df = filtered_examples_data()
        if df.empty:
            return ui.div("No examples available with current filters", 
                            style="text-align: center; padding: 40px; color: #36464B;")
        
        # Filter out extreme scores (>90 or <10)
        df_filtered = df[(df['Compliance Level'] <= 90) & (df['Compliance Level'] >= 10)]
        
        if df_filtered.empty:
            return ui.div("No examples in the 10-90% range", 
                            style="text-align: center; padding: 40px; color: #36464B;")
        
        df_sorted = df_filtered.sort_values('Compliance Level', ascending=False)
        
        # Get top 5 and bottom 5
        top_5 = df_sorted.head(5)
        bottom_5 = df_sorted.tail(5)
        
        def extract_direct_quotes(rationale, is_positive=False):
            """Extract actionable quotes from rationale"""
            if not rationale or len(str(rationale)) < 20:
                return "Review content for accessibility improvements"
                
            rationale_str = str(rationale).lower()
            
            if is_positive:
                # Look for positive aspects for top performers
                positive_quotes = []
                
                if 'clear' in rationale_str and any(word in rationale_str for word in ['structure', 'language', 'content']):
                    sentences = rationale_str.split('.')
                    for sentence in sentences:
                        if 'clear' in sentence and any(word in sentence for word in ['structure', 'language', 'content']):
                            positive_quotes.append(sentence.strip().capitalize())
                            break
                
                if 'simple' in rationale_str and any(word in rationale_str for word in ['sentences', 'vocabulary', 'language']):
                    sentences = rationale_str.split('.')
                    for sentence in sentences:
                        if 'simple' in sentence and any(word in sentence for word in ['sentences', 'vocabulary', 'language']):
                            positive_quotes.append(sentence.strip().capitalize())
                            break
                
                if 'good' in rationale_str or 'well' in rationale_str:
                    sentences = rationale_str.split('.')
                    for sentence in sentences:
                        if 'good' in sentence or 'well' in sentence:
                            positive_quotes.append(sentence.strip().capitalize())
                            break
                
                if 'accessible' in rationale_str and 'format' in rationale_str:
                    sentences = rationale_str.split('.')
                    for sentence in sentences:
                        if 'accessible' in sentence and 'format' in sentence:
                            positive_quotes.append(sentence.strip().capitalize())
                            break
                
                return positive_quotes[0] if positive_quotes else "Content demonstrates good accessibility practices"
            
            else:
                # Look for improvement areas for bottom performers
                quotes = []
                
                if 'change' in rationale_str and any(word in rationale_str for word in ['word', 'term', 'phrase']):
                    sentences = rationale_str.split('.')
                    for sentence in sentences:
                        if 'change' in sentence and any(word in sentence for word in ['word', 'term', 'phrase']):
                            quotes.append(sentence.strip().capitalize())
                            break
                
                if 'explain' in rationale_str or 'define' in rationale_str:
                    sentences = rationale_str.split('.')
                    for sentence in sentences:
                        if 'explain' in sentence or 'define' in sentence:
                            quotes.append(sentence.strip().capitalize())
                            break
                
                if 'simplify' in rationale_str:
                    sentences = rationale_str.split('.')
                    for sentence in sentences:
                        if 'simplify' in sentence:
                            quotes.append(sentence.strip().capitalize())
                            break
                            
                if 'avoid' in rationale_str:
                    sentences = rationale_str.split('.')
                    for sentence in sentences:
                        if 'avoid' in sentence:
                            quotes.append(sentence.strip().capitalize())
                            break
                
                return quotes[0] if quotes else "Improve content clarity and accessibility"
        
        def create_example_card(example, rank_label):
            score = example['Compliance Level']
            url = example['URL']
            page_type = example['Page Type']
            language = example.get('Language', 'Unknown')
            rationale = example.get('Rationale', '')
            
            # Get direct quote
            is_top_performer = 'Top' in rank_label
            direct_quote = extract_direct_quotes(rationale, is_positive=is_top_performer)
            
            def get_score_badge_style(score):
                if score >= 80:
                    return "background: #242D31; color: #F7E194;"
                elif score >= 70:
                    return "background: #36464B; color: #F7E194;"
                elif score >= 60:
                    return "background: #8C9091; color: white;"
                else:
                    return "background: #d1d5db; color: #242D31;"
            
            def shorten_url(url, max_length=45):
                if len(url) <= max_length:
                    return url
                return url[:max_length-3] + "..."
            
            # Different styling for positive vs negative feedback
            label_text = "✨ What's working:" if is_top_performer else "📝 Action needed:"
            border_color = "#059669" if is_top_performer else "#F7E194"
            
            return ui.div(
                # Header
                ui.div(
                    ui.h5(rank_label, style="margin: 0; color: #242D31; font-size: 18px;"),
                    ui.span(f"{score:.0f}%", 
                            class_="score-badge",
                            style=get_score_badge_style(score)),
                    style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;"
                ),
                
                # URL and details
                ui.div(
                    ui.code(shorten_url(url), style="background: #F2F3EF; padding: 2px 6px; border-radius: 4px; color: #242D31; font-size: 15px;"),
                    create_copy_button(url),
                    style="margin-bottom: 8px; display: flex; align-items: center;"
                ),
                ui.div(
                    ui.span(f"{page_type} • {language}", style="color: #36464B; font-size: 16px;"),
                    style="margin-bottom: 10px;"
                ),
                
                # Direct quote from rationale
                ui.div(
                    ui.strong(label_text, style="color: #242D31; font-size: 16px;"),
                    ui.br(),
                    ui.span(f'"{direct_quote}"', style="font-style: italic; color: #36464B; font-size: 16px;"),
                    style=f"background: #FAFAF9; padding: 10px; border-radius: 8px; border-left: 3px solid {border_color};"
                ),
                
                style="background: #ffffff; border: 1px solid var(--neutral-light); border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);"
            )
        
        # Create cards for top 5 and bottom 5
        top_cards = [create_example_card(top_5.iloc[i], f"🌟 Top #{i+1}") for i in range(len(top_5))]
        bottom_cards = [create_example_card(bottom_5.iloc[i], f"🔧 Needs Work #{len(bottom_5)-i}") for i in range(len(bottom_5))]
        
        return ui.div(
            ui.row(
                ui.column(6, 
                    ui.h4("Top Pages", style="color: #242D31; margin-bottom: 20px;"),
                    ui.div(top_cards)
                ),
                ui.column(6,
                    ui.h4("Pages Needing Attention", style="color: #242D31; margin-bottom: 20px;"),
                    ui.div(bottom_cards)
                )
            )
        )
    @output
    @render.ui
    def key_insights_unfiltered():
        if not authenticated.get():
            return ui.div()
            
        # Always use full dataset for unfiltered key insights (never use filtered data)
        full_df = bank_data.get()
        
        if full_df is None or full_df.empty:
            return ui.div("No data available for analysis.")
        
        # Always use full dataset for overall insights
        df_for_insights = full_df
        total_pages = len(df_for_insights)
        
        # Generate detailed business insights
        avg_score = df_for_insights['Compliance Level'].mean()
        
        # Language analysis
        if 'Language' in df_for_insights.columns and len(df_for_insights['Language'].unique()) > 1:
            lang_performance = df_for_insights.groupby('Language')['Compliance Level'].mean().sort_values(ascending=False)
            best_lang = lang_performance.index[0]
            worst_lang = lang_performance.index[-1]
            lang_diff = lang_performance.iloc[0] - lang_performance.iloc[-1]
            
            lang_insight = f"🌍 Language Performance: {best_lang} content outperforms {worst_lang} by {lang_diff:.0f} percentage points. Consider standardizing content practices across languages."
        else:
            lang_insight = f"🌍 Language Coverage: Analysis covers {df_for_insights['Language'].unique()[0] if len(df_for_insights) > 0 else 'mixed'} language content."
        
        # Page type analysis
        if 'Page Type' in df_for_insights.columns and len(df_for_insights['Page Type'].unique()) > 1:
            page_performance = df_for_insights.groupby('Page Type')['Compliance Level'].mean().sort_values(ascending=False)
            best_page_type = page_performance.index[0]
            worst_page_type = page_performance.index[-1]
            
            page_insight = f"📄 Content Type Analysis: {best_page_type} pages achieve {page_performance.iloc[0]:.0f}% compliance vs {worst_page_type} pages at {page_performance.iloc[-1]:.0f}%. Focus improvement efforts on {worst_page_type} content."
        else:
            page_insight = f"📄 Content Focus: Analysis covers {df_for_insights['Page Type'].unique()[0] if len(df_for_insights) > 0 else 'mixed'} page types."
        
        # Compliance distribution analysis
        compliant_pages = len(df_for_insights[df_for_insights['Compliance Level'] >= 70])
        compliance_rate = (compliant_pages / total_pages * 100) if total_pages > 0 else 0
        
        # Score distribution insights
        high_performers = len(df_for_insights[df_for_insights['Compliance Level'] >= 80])
        low_performers = len(df_for_insights[df_for_insights['Compliance Level'] < 60])
        
        if high_performers > 0 and low_performers > 0:
            distribution_insight = f"📊 Performance Distribution: {high_performers} pages ({high_performers/total_pages*100:.0f}%) are high performers (80%+) while {low_performers} pages ({low_performers/total_pages*100:.0f}%) need immediate attention (<60%). Strong opportunity for knowledge transfer from top performers."
        elif high_performers > 0:
            distribution_insight = f"📊 Strong Foundation: {high_performers} pages ({high_performers/total_pages*100:.0f}%) achieve excellent scores (80%+). Use these as templates for improving remaining content."
        else:
            distribution_insight = f"📊 Improvement Opportunity: {compliance_rate:.0f}% compliance rate indicates significant room for accessibility enhancement across all content types."
        
        # Actionable recommendations
        if avg_score >= 75:
            action_insight = f"✅ Next Steps: With {avg_score:.0f}% average performance, focus on elevating remaining non-compliant pages to meet the 70% threshold. Estimated 4-6 weeks for full compliance with targeted content review."
        elif avg_score >= 65:
            action_insight = f"⚠️ Priority Actions: {avg_score:.0f}% average suggests systematic issues. Recommend comprehensive content audit and staff training. Target: 15-20% improvement achievable in 8-10 weeks."
        else:
            action_insight = f"🚨 Urgent Intervention: {avg_score:.0f}% average requires immediate action. Suggest content rewrite program and accessibility training. Realistic timeline: 12-16 weeks for substantial improvement."
        
        # Analyze common issues from rationale data
        rationale_insights = []
        if 'Rationale' in df_for_insights.columns:
            all_rationales = ' '.join(df_for_insights['Rationale'].fillna('').astype(str)).lower()
            
            # Common vocabulary issues
            if 'technical terms' in all_rationales or 'banking terms' in all_rationales:
                rationale_insights.append("🔤 Vocabulary Challenge: Technical banking terminology appears frequently across pages, requiring simplification for B2 compliance")
            
            # Grammar patterns
            if 'complex sentences' in all_rationales:
                rationale_insights.append("📝 Sentence Structure: Multiple pages contain complex sentence structures that could be simplified for better comprehension")
            elif 'simple' in all_rationales and 'structures' in all_rationales:
                rationale_insights.append("📝 Grammar Strength: Pages generally use clear, simple sentence structures supporting accessibility")
                
            # Clarity and coherence issues
            if 'transitions' in all_rationales and ('weak' in all_rationales or 'poor' in all_rationales):
                rationale_insights.append("🔗 Content Flow: Weak transitions between sections identified as a recurring issue across multiple pages")
            
            if 'disjointed' in all_rationales or 'coherence' in all_rationales:
                rationale_insights.append("📋 Content Organization: Content coherence needs improvement to support better user comprehension")
        
        # Build insights list
        insights = []
        
        # Add rationale-based insights if available
        if rationale_insights:
            insights.extend(rationale_insights[:2])  # Include top 2 rationale insights
            
        # Add performance insights
        insights.extend([
            f"🎯 Overall Performance: {avg_score:.0f}% average compliance across entire website ({compliance_rate:.0f}% of pages meet B2 standards)",
            lang_insight,
            page_insight,
            distribution_insight,
            action_insight
        ])
        
        return ui.div([
            ui.div(
                insight, 
                style="margin: 12px 0; padding: 12px; background: #FAFAF9; border-radius: 8px; color: #242D31; border-left: 3px solid #F7E194;"
            ) 
            for insight in insights
        ])

# Create the app
app = App(app_ui, server)

if __name__ == "__main__":
    app.run()