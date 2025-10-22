#!/bin/bash

# Dobbs.pdf Comprehensive Testing Framework
# Run script for executing tests and generating reports

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="/srv/luris/be/entity-extraction-service/venv"
RESULTS_DIR="$SCRIPT_DIR/results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Dobbs.pdf Extraction Testing Framework${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    echo "Please create it first with: python3 -m venv $VENV_DIR"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Create results directory if it doesn't exist
mkdir -p "$RESULTS_DIR"

# Check if services are running
echo -e "${YELLOW}Checking service health...${NC}"

check_service() {
    local service_name=$1
    local port=$2
    local endpoint=$3
    
    if curl -s -f "http://localhost:${port}${endpoint}" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ ${service_name} (port ${port}) is running${NC}"
        return 0
    else
        echo -e "${RED}✗ ${service_name} (port ${port}) is not running${NC}"
        return 1
    fi
}

# Check required services
SERVICES_OK=true
check_service "Document Upload Service" 8008 "/api/v1/health" || SERVICES_OK=false
check_service "Entity Extraction Service" 8007 "/api/v1/health" || SERVICES_OK=false

if [ "$SERVICES_OK" = false ]; then
    echo -e "${RED}Some required services are not running.${NC}"
    echo "Please start them with:"
    echo "  sudo systemctl start luris-document-upload"
    echo "  sudo systemctl start luris-entity-extraction"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Parse command line arguments
ACTION=${1:-"test"}
ANALYSIS_TYPE=${2:-"both"}

case "$ACTION" in
    test)
        echo -e "\n${YELLOW}Running comprehensive extraction test...${NC}"
        echo "This may take several minutes for the Dobbs document."
        
        python3 "$SCRIPT_DIR/dobbs_comprehensive_test.py"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Test completed successfully${NC}"
            
            # Automatically run visual analysis on the latest results
            echo -e "\n${YELLOW}Generating visual quality report...${NC}"
            python3 "$SCRIPT_DIR/visual_quality_inspector.py" --latest --format "$ANALYSIS_TYPE"
            
            echo -e "\n${YELLOW}Generating entity type analysis...${NC}"
            python3 "$SCRIPT_DIR/entity_type_analyzer.py" --latest --format "$ANALYSIS_TYPE"
        else
            echo -e "${RED}✗ Test failed${NC}"
            exit 1
        fi
        ;;
        
    analyze)
        if [ -z "$2" ]; then
            echo -e "${YELLOW}Analyzing latest results...${NC}"
            python3 "$SCRIPT_DIR/visual_quality_inspector.py" --latest --format both
            python3 "$SCRIPT_DIR/entity_type_analyzer.py" --latest --format both
        else
            echo -e "${YELLOW}Analyzing results from: $2${NC}"
            python3 "$SCRIPT_DIR/visual_quality_inspector.py" --results-file "$2" --format both
            python3 "$SCRIPT_DIR/entity_type_analyzer.py" --results-file "$2" --format both
        fi
        ;;
        
    visual)
        echo -e "${YELLOW}Running visual quality inspector...${NC}"
        python3 "$SCRIPT_DIR/visual_quality_inspector.py" --latest --format both
        ;;
        
    types)
        echo -e "${YELLOW}Running entity type analyzer...${NC}"
        python3 "$SCRIPT_DIR/entity_type_analyzer.py" --latest --format both
        ;;
        
    clean)
        echo -e "${YELLOW}Cleaning old results (keeping last 5)...${NC}"
        cd "$RESULTS_DIR"
        ls -t dobbs_test_*.json 2>/dev/null | tail -n +6 | xargs -r rm -v
        ls -t visual_analysis_*.* 2>/dev/null | tail -n +6 | xargs -r rm -v
        ls -t entity_type_analysis_*.* 2>/dev/null | tail -n +6 | xargs -r rm -v
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;
        
    help)
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  test [format]     - Run comprehensive test and generate reports"
        echo "                      format: json|markdown|both (default: both)"
        echo "  analyze [file]    - Analyze existing results (latest if no file specified)"
        echo "  visual            - Run only visual quality inspector on latest results"
        echo "  types             - Run only entity type analyzer on latest results"
        echo "  clean             - Clean old results (keep last 5 of each type)"
        echo "  help              - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 test           - Run full test suite with all reports"
        echo "  $0 test json      - Run tests and generate JSON reports only"
        echo "  $0 analyze        - Analyze latest test results"
        echo "  $0 analyze results/dobbs_test_20240101_120000.json"
        ;;
        
    *)
        echo -e "${RED}Unknown command: $ACTION${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

# Show results location
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Results saved in: $RESULTS_DIR${NC}"
echo -e "${GREEN}========================================${NC}"

# List recent results
echo -e "\nRecent results:"
ls -lt "$RESULTS_DIR" 2>/dev/null | head -6 | tail -5

# Deactivate virtual environment
deactivate