

from fastapi import HTTPException, Depends, Request
from firebase_admin import auth as firebase_auth
from functools import lru_cache


async def verify_token(request: Request) -> dict:
    
    #verify Firebase ID token from Authorization header.
    
    
    
    auth_header = request.headers.get("Authorization")#authorisatioh header- a header in the content returned from requests
    #print(f"Auth header received: {auth_header[:50] if auth_header else 'NONE'}")
    if not auth_header:
        print("No auth header")
        raise HTTPException(
            
            status_code=401,
            detail="Missing Authorization header"
        )
        
    
  
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Use: Bearer <token>"
        )
    
    #verifying tokens with firebase
    try:
        
        #print("TOKEN LENGTH:", len(token))
        #print("TOKEN START:", token[:30])


        decoded = firebase_auth.verify_id_token(token)
        #print(f"Token verified for: {decoded['uid']}")
        return decoded
    except Exception as e:
        #print(f"Verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Verification failed: {str(e)}")


    
    """except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid ID token"
        )
    
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="ID token expired. Please login again."
        )
    
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=401,
            detail="ID token has been revoked"
        )
   
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}"
        )"""

"""
async def get_current_uid(user=Depends(verify_token)) -> str:
  

    return user.get('uid')



async def get_current_email(user=Depends(verify_token)) -> str:
   
    return user.get('email')"""